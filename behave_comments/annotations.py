"""Annotation extraction from .feature file comments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from behave_comments.errors import AnnotationParseError
from behave_comments.models import Annotation

_ANNOTATION_RE = re.compile(
    r"^#\s*@(?P<key>[\w-]+)[.:=]{0,2}\s*(?P<value>.*)$"
)


_LIFECYCLE_PREFIX_RE = re.compile(
    r"^#\s*@(?P<hook>before|after)-(?P<scope>feature|scenario|step|all)\s*:",
    re.IGNORECASE,
)


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

    annotations: list[Annotation] = []
    current_scope = "feature"
    current_scope_name = ""
    pending: list[Annotation] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        ann = parse_annotation_line(line, line_number)
        if ann is not None:
            pending.append(ann)
            continue

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("Feature:"):
            current_scope = "feature"
            current_scope_name = stripped.removeprefix("Feature:").strip()
        elif stripped.startswith("Background:"):
            current_scope = "background"
            current_scope_name = "Background"
        elif stripped.startswith("Scenario Outline:") or stripped.startswith("Scenario Template:"):
            current_scope = "scenario"
            if stripped.startswith("Scenario Outline:"):
                current_scope_name = stripped.removeprefix("Scenario Outline:").strip()
            else:
                current_scope_name = stripped.removeprefix("Scenario Template:").strip()
        elif stripped.startswith("Scenario:"):
            current_scope = "scenario"
            current_scope_name = stripped.removeprefix("Scenario:").strip()
        elif stripped.startswith("Rule:"):
            current_scope = "rule"
            current_scope_name = stripped.removeprefix("Rule:").strip()
        elif stripped.startswith("Examples:"):
            current_scope = "examples"
            current_scope_name = "Examples"
        else:
            first_word = stripped.split(None, 1)[0]
            if first_word in ("Given", "When", "Then", "And", "But", "*"):
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

    metadata: dict[str, list[dict[str, str]]] = {}
    for ann in annotations:
        scope_key = ann.scope
        if scope_key not in metadata:
            metadata[scope_key] = []
        metadata[scope_key].append(
            {
                "key": ann.key,
                "value": ann.value,
                "line": str(ann.line),
                "scope_name": ann.scope_name,
            }
        )

    setattr(context, prefix, metadata)
