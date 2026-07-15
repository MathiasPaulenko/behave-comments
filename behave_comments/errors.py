"""Exception hierarchy for behave-comments."""

from __future__ import annotations


class BehaveCommentsError(Exception):
    """Base exception for all behave-comments errors."""


class ContentTypeError(BehaveCommentsError):
    """Raised when an unsupported or invalid content type is detected."""

    def __init__(self, content_type: str) -> None:
        self.content_type = content_type
        super().__init__(f"Unsupported content type: {content_type!r}")


class ParseError(BehaveCommentsError):
    """Raised when parsing a text block fails."""

    def __init__(self, content_type: str, detail: str, line: int | None = None) -> None:
        self.content_type = content_type
        self.detail = detail
        self.line = line
        location = f" at line {line}" if line is not None else ""
        super().__init__(f"Failed to parse {content_type!r} content{location}: {detail}")


class MissingDependencyError(BehaveCommentsError):
    """Raised when an optional dependency is not installed."""

    def __init__(self, dependency: str, extra: str) -> None:
        self.dependency = dependency
        self.extra = extra
        super().__init__(
            f"Missing dependency: {dependency!r}. "
            f"Install it with: pip install behave-comments[{extra}]"
        )


class AnnotationParseError(BehaveCommentsError):
    """Raised when parsing an annotation from a comment fails."""

    def __init__(self, line: int, raw: str) -> None:
        self.line = line
        self.raw = raw
        super().__init__(f"Invalid annotation at line {line}: {raw!r}")


class LifecycleStepError(BehaveCommentsError):
    """Raised when a lifecycle hook step fails to execute."""

    def __init__(self, hook_type: str, step_text: str, detail: str) -> None:
        self.hook_type = hook_type
        self.step_text = step_text
        self.detail = detail
        super().__init__(
            f"Lifecycle step failed in {hook_type!r} hook: {step_text!r} — {detail}"
        )
