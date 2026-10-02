"""Annotation extraction from .feature file comments."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from behave_comments.errors import AnnotationParseError
from behave_comments.models import Annotation

_ANNOTATION_RE = re.compile(r"^#\s*@(?P<key>[\w-]+)[.:=]{0,2}\s*(?P<value>.*)$")


_LIFECYCLE_PREFIX_RE = re.compile(
    r"^#\s*@(?P<hook>before|after)-(?P<scope>feature|scenario|step|all)\s*:",
    re.IGNORECASE,
)

_LANGUAGE_RE = re.compile(r"^#\s*language\s*:\s*(?P<lang>[\w-]+)")

_DOCSTRING_DELIMITERS = ('"""', "'''")

# Fallback English keywords (same values as behave.i18n.languages["en"]).
_EN_KEYWORDS: dict[str, list[str]] = {
    "feature": ["Feature", "Business Need", "Ability"],
    "rule": ["Rule"],
    "background": ["Background"],
    "scenario": ["Example", "Scenario"],
    "scenario_outline": ["Scenario Outline", "Scenario Template"],
    "examples": ["Examples", "Scenarios"],
    "given": ["* ", "Given "],
    "when": ["* ", "When "],
    "then": ["* ", "Then "],
    "and": ["* ", "And "],
    "but": ["* ", "But "],
}


def _iter_code_lines(content: str) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, line)`` pairs, skipping doc string bodies.

    Doc strings (``\"\"\"`` or ``'''`` blocks) may contain text that looks
    like comments, annotations or Gherkin keywords; they must not be
    interpreted as such.
    """
    delimiter = ""
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if delimiter:
            if stripped.startswith(delimiter):
                delimiter = ""
            continue
        if stripped.startswith(_DOCSTRING_DELIMITERS):
            # A one-line doc string like \"\"\"text\"\"\" does not open a block.
            if not stripped[3:].endswith(stripped[:3]):
                delimiter = stripped[:3]
            continue
        yield line_number, line


def _detect_language(content: str) -> str:
    """Return the Gherkin language code declared by ``# language: xx``."""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _LANGUAGE_RE.match(stripped)
        return match.group("lang") if match else "en"
    return "en"


def _keyword_map(language: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Build (statement_keywords, step_keywords) for a Gherkin language.

    Statement keywords map to scopes and are sorted longest-first so
    ``Scenario Outline`` wins over ``Scenario``. Step keywords keep their
    raw form (trailing space or ``*`` suffix as used by behave.i18n).
    """
    try:
        from behave.i18n import languages

        data = languages.get(language) or languages["en"]
    except ImportError:
        data = _EN_KEYWORDS

    statements: list[tuple[str, str]] = []
    for i18n_key, scope in (
        ("scenario_outline", "scenario"),
        ("scenario", "scenario"),
        ("rule", "rule"),
        ("background", "background"),
        ("examples", "examples"),
        ("feature", "feature"),
    ):
        for keyword in data.get(i18n_key) or []:
            keyword = keyword.rstrip("* ")
            if keyword:
                statements.append((keyword, scope))
    statements.sort(key=lambda item: len(item[0]), reverse=True)

    step_keywords: list[str] = []
    for i18n_key in ("given", "when", "then", "and", "but"):
        for keyword in data.get(i18n_key) or []:
            keyword = keyword.strip()
            if keyword:
                step_keywords.append(keyword)

    return statements, step_keywords


def _match_step_keyword(stripped: str, step_keywords: list[str]) -> bool:
    """Return True if the line starts with a step keyword."""
    for keyword in step_keywords:
        if keyword == "*":
            if stripped == "*" or stripped.startswith("* "):
                return True
        elif stripped == keyword or stripped.startswith(keyword + " "):
            return True
    return False


def parse_annotation_line(line: str, line_number: int) -> Annotation | None:
    """Parse a single comment line as an annotation.

    Supports three syntaxes:
        # @key value
        # @key: value
        # @key=value

    Lines that look like lifecycle hooks (``# @before-*:`` or
    ``# @after-*:``) are **not** annotations and return None.

    Args:
        line: The comment line to parse.
        line_number: The line number in the file.

    Returns:
        An Annotation if the line is a valid annotation, or None
        if the line is a comment but not an annotation.

    Raises:
        AnnotationParseError: If the line looks like an annotation
            (starts with ``# @``) but has an invalid key.
    """
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None

    if _LIFECYCLE_PREFIX_RE.match(stripped):
        return None

    match = _ANNOTATION_RE.match(stripped)
    if match is None:
        if stripped.startswith("# @"):
            raise AnnotationParseError(line=line_number, raw=stripped)
        return None

    key = match.group("key")
    value = match.group("value").strip()

    return Annotation(
        key=key,
        value=value,
        line=line_number,
        scope="",
        scope_name="",
    )


def extract_annotations(feature_path: str | Path) -> list[Annotation]:
    """Extract all annotations from a .feature file with scope detection.

    Reads the raw .feature file (not via Behave, since Behave strips comments)
    and assigns each annotation its Gherkin scope.

    Args:
        feature_path: Path to the .feature file.

    Returns:
        A list of Annotations with scope and scope_name assigned.

    Raises:
        FileNotFoundError: If the file does not exist.
        AnnotationParseError: If a malformed annotation is found.
    """
    path = Path(feature_path)
    content = path.read_text(encoding="utf-8-sig")

    statements, step_keywords = _keyword_map(_detect_language(content))

    annotations: list[Annotation] = []
    current_scope = "feature"
    current_scope_name = ""
    pending: list[Annotation] = []

    for line_number, line in _iter_code_lines(content):
        stripped = line.strip()

        ann = parse_annotation_line(line, line_number)
        if ann is not None:
            pending.append(ann)
            continue

        if not stripped or stripped.startswith("#"):
            continue

        matched = False
        for keyword, scope in statements:
            if stripped.startswith(keyword + ":"):
                current_scope = scope
                # Background/Examples carry no meaningful name.
                if scope in ("background", "examples"):
                    current_scope_name = keyword
                else:
                    current_scope_name = stripped[len(keyword) + 1 :].strip()
                matched = True
                break

        if not matched:
            if _match_step_keyword(stripped, step_keywords):
                current_scope = "step"
                current_scope_name = stripped
            else:
                continue

        for p in pending:
            annotations.append(
                Annotation(
                    key=p.key,
                    value=p.value,
                    line=p.line,
                    scope=current_scope,
                    scope_name=current_scope_name,
                )
            )
        pending.clear()

    for p in pending:
        annotations.append(
            Annotation(
                key=p.key,
                value=p.value,
                line=p.line,
                scope=current_scope,
                scope_name=current_scope_name,
            )
        )

    return annotations


_TAG_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9-]+")
_TAG_COLLAPSE_RE = re.compile(r"-{2,}")


def annotations_to_tags(
    annotations: list[Annotation],
    *,
    dedup: bool = False,
) -> list[str]:
    """Convert annotations to Behave-compatible tag strings.

    Tags are formatted as ``@key-value`` (hyphen-separated) or ``@key``
    if the value is empty. All non-alphanumeric characters in keys and
    values (except hyphens) are replaced with hyphens.

    Args:
        annotations: A list of Annotation objects.
        dedup: If True, remove duplicate tags while preserving order.

    Returns:
        A list of tag strings (with ``@`` prefix).
    """
    tags: list[str] = []
    seen: set[str] = set()
    for ann in annotations:
        sanitized_key = _TAG_SANITIZE_RE.sub("-", ann.key)
        sanitized_key = _TAG_COLLAPSE_RE.sub("-", sanitized_key).strip("-")
        if not sanitized_key:
            continue
        if ann.value.strip():
            sanitized = _TAG_SANITIZE_RE.sub("-", ann.value)
            sanitized = _TAG_COLLAPSE_RE.sub("-", sanitized).strip("-")
            tag = f"@{sanitized_key}-{sanitized}" if sanitized else f"@{sanitized_key}"
        else:
            tag = f"@{sanitized_key}"
        if dedup:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
        else:
            tags.append(tag)
    return tags


def inject_metadata(
    context: Any,
    feature: Any,
    *,
    prefix: str = "metadata",
) -> None:
    """Inject annotations as metadata into Behave's context.

    Reads the feature file, extracts annotations, and stores them
    in ``context.{prefix}`` as a dict mapping scope to list of annotations.

    Args:
        context: Behave's context object.
        feature: The Behave feature object (must have ``filename`` attribute).
        prefix: The attribute name to store metadata under.
            Defaults to ``"metadata"``.
    """
    filename = getattr(feature, "filename", None)
    if not filename:
        return

    annotations = extract_annotations(filename)

    metadata: dict[str, list[dict[str, Any]]] = {}
    for ann in annotations:
        scope_key = ann.scope
        if scope_key not in metadata:
            metadata[scope_key] = []
        metadata[scope_key].append(
            {
                "key": ann.key,
                "value": ann.value,
                "line": ann.line,
                "scope_name": ann.scope_name,
            }
        )

    setattr(context, prefix, metadata)
