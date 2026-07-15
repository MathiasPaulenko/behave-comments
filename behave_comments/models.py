"""Data models for behave-comments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TextBlock:
    """A parsed text block from a Behave doc string.

    Attributes:
        content: The raw text content (without the content type line).
        content_type: The detected content type (e.g. "json", "text/plain").
        line: The line number in the feature file where the text block starts.
        parsed: The parsed Python object, or None if not yet parsed.
    """

    content: str
    content_type: str
    line: int
    parsed: Any | None = None


@dataclass(frozen=True, slots=True)
class Annotation:
    """A structured annotation extracted from a comment.

    Attributes:
        key: The annotation key (e.g. "jira", "priority").
        value: The annotation value (e.g. "TICKET-42", "high").
        line: The line number in the feature file where the comment appears.
        scope: The Gherkin scope (e.g. "feature", "scenario", "step").
        scope_name: The name of the Gherkin element (e.g. "Login", "Given the db").
    """

    key: str
    value: str
    line: int
    scope: str
    scope_name: str
