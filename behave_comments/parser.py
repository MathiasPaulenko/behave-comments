"""Text block parser for behave-comments."""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from behave_comments.errors import ContentTypeError, ParseError
from behave_comments.models import TextBlock

SUPPORTED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "text/plain",
        "json",
        "yaml",
        "xml",
        "csv",
        "form-urlencoded",
        "graphql",
    }
)

_TRIPLE_QUOTE_RE = re.compile(r'^(?:"""|\'\'\')(\s*(\S+)?\s*)?$')


def detect_content_type(opening_line: str) -> str:
    """Detect the content type from a triple-quote opening line.

    Args:
        opening_line: The line that opens a doc string, e.g. ``\"\"\"json``
            or ``'''yaml``.

    Returns:
        The normalized content type string (lowercase).

    Raises:
        ContentTypeError: If the line is not a valid triple-quote opening
            or the content type is not supported.
    """
    match = _TRIPLE_QUOTE_RE.match(opening_line)
    if match is None:
        raise ContentTypeError(opening_line)

    raw = match.group(2)
    if raw is None:
        return "text/plain"

    content_type = raw.lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ContentTypeError(content_type)

    return content_type


def _parse_text_plain(text: str) -> str:
    """Parse text/plain content. Returns the text unchanged."""
    return text


def _parse_graphql(text: str) -> str:
    """Parse graphql content. Returns the text unchanged (raw query string)."""
    return text


def _parse_json(text: str) -> Any:
    """Parse JSON content.

    Args:
        text: The JSON string to parse.

    Returns:
        The parsed Python object.

    Raises:
        ParseError: If the JSON is invalid.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ParseError(
            content_type="json",
            detail=str(e),
            line=e.lineno,
        ) from e


def _parse_csv(text: str) -> list[dict[str, str]]:
    """Parse CSV content into a list of dictionaries.

    Args:
        text: The CSV text to parse.

    Returns:
        A list of dictionaries, one per row, keyed by the header row.

    Raises:
        ParseError: If the CSV is invalid.
    """
    try:
        reader = csv.DictReader(io.StringIO(text))
        return [{k: v for k, v in row.items() if k is not None and v is not None} for row in reader]
    except csv.Error as e:
        raise ParseError(
            content_type="csv",
            detail=str(e),
            line=None,
        ) from e


def _parse_form_urlencoded(text: str) -> dict[str, list[str]]:
    """Parse form-urlencoded content into a dictionary of lists.

    Args:
        text: The form-urlencoded string to parse.

    Returns:
        A dictionary mapping keys to lists of values.
    """
    return urllib.parse.parse_qs(text, keep_blank_values=True)


def _parse_xml(text: str) -> Any:
    """Parse XML content into an ElementTree Element.

    Args:
        text: The XML string to parse.

    Returns:
        The root Element of the parsed XML.

    Raises:
        ParseError: If the XML is invalid.
    """
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        raise ParseError(
            content_type="xml",
            detail=str(e),
            line=getattr(e, "position", (None,))[0],
        ) from e


def _parse_yaml(text: str) -> Any:
    """Parse YAML content.

    Args:
        text: The YAML string to parse.

    Returns:
        The parsed Python object (dict, list, str, int, etc.).
        Returns None for empty or whitespace-only input.

    Raises:
        ParseError: If the YAML is invalid.
    """
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = mark.line + 1 if mark is not None else None
        raise ParseError(
            content_type="yaml",
            detail=str(e),
            line=line,
        ) from e


_PARSERS: dict[str, Callable[[str], Any]] = {
    "text/plain": _parse_text_plain,
    "json": _parse_json,
    "yaml": _parse_yaml,
    "xml": _parse_xml,
    "csv": _parse_csv,
    "form-urlencoded": _parse_form_urlencoded,
    "graphql": _parse_graphql,
}


def parse_text(text: str, content_type: str = "text/plain") -> Any:
    """Parse a text block according to its content type.

    Args:
        text: The text content to parse.
        content_type: The content type (case-insensitive).
            Defaults to ``"text/plain"``.

    Returns:
        The parsed Python object.

    Raises:
        ContentTypeError: If the content type is not supported.
        ParseError: If parsing fails.
    """
    if content_type is None:
        raise ContentTypeError("None")
    normalized = content_type.strip().lower()
    if normalized not in SUPPORTED_CONTENT_TYPES:
        raise ContentTypeError(content_type)

    parser = _PARSERS[normalized]
    return parser(text)


_DOCSTRING_OPEN_RE = re.compile(r'^(?:"""|\'\'\')\s*(\S*)\s*$')


def _declared_content_type(source: Any, text: Any) -> str | None:
    """Return the content type declared for a doc string, if any.

    Behave discards the media type written on the doc string opening line
    (``\"\"\"json``) and always stores ``text/plain``. This function recovers
    it from ``text.content_type`` (future Behave versions) or by reading the
    opening line of the doc string back from the feature file.

    Args:
        source: A Behave step or context object.
        text: The doc string text (may be a ``behave.model.Text``).

    Returns:
        The declared content type, or None if none was declared.

    Raises:
        ContentTypeError: If a media type was declared but is not supported.
    """
    declared = getattr(text, "content_type", None)
    if declared:
        normalized = str(declared).strip().lower()
        if normalized != "text/plain":
            if normalized not in SUPPORTED_CONTENT_TYPES:
                raise ContentTypeError(normalized)
            return normalized

    line_no = getattr(text, "line", None)
    if not line_no:
        return None

    filename = getattr(source, "filename", None)
    if filename is None:
        feature = getattr(source, "feature", None)
        filename = getattr(feature, "filename", None)
    if not filename:
        return None

    try:
        opening = Path(filename).read_text(encoding="utf-8-sig").splitlines()[line_no - 1].strip()
    except (OSError, IndexError):
        return None

    match = _DOCSTRING_OPEN_RE.match(opening)
    if match is None or not match.group(1):
        return None

    content_type = match.group(1).lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ContentTypeError(content_type)
    return content_type


def extract_text_block(step: Any) -> TextBlock | None:
    """Extract and parse a text block from a Behave step or context.

    The content type is resolved in this order:

    1. Declared on the doc string opening line (``\"\"\"json``), recovered
       from the feature file since Behave discards it.
    2. As the first line inside the doc string body.
    3. ``text/plain`` as fallback.

    Args:
        step: A Behave step object, or the Behave ``context`` during a step
            (``context.text`` holds the doc string).

    Returns:
        A TextBlock with the parsed content, or None if the step
        has no text block.

    Raises:
        ContentTypeError: If a declared content type is not supported.
        ParseError: If parsing fails.
    """
    text = getattr(step, "text", None)
    if not text:
        return None

    content_type = _declared_content_type(step, text)
    content = str(text)

    if content_type is None:
        lines = content.split("\n", 1)
        first_line = lines[0].strip().lower()
        if len(lines) > 1 and first_line in SUPPORTED_CONTENT_TYPES:
            content_type = first_line
            content = lines[1]
        else:
            content_type = "text/plain"

    parsed = parse_text(content, content_type)
    line = getattr(step, "line", 0)

    return TextBlock(
        content=content,
        content_type=content_type,
        line=line,
        parsed=parsed,
    )
