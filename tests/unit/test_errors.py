"""Tests for the behave-comments exception hierarchy."""

from __future__ import annotations

import pytest

from behave_comments.errors import (
    AnnotationParseError,
    BehaveCommentsError,
    ContentTypeError,
    LifecycleStepError,
    ParseError,
)


@pytest.mark.parametrize(
    ("exc_class", "args"),
    [
        (ContentTypeError, ("xml",)),
        (ParseError, ("json", "Expecting value", 3)),
        (AnnotationParseError, (5, "# @key")),
        (LifecycleStepError, ("before-feature", "Given the db", "Step not found")),
    ],
)
def test_all_exceptions_inherit_from_base(
    exc_class: type[Exception], args: tuple[object, ...]
) -> None:
    assert issubclass(exc_class, BehaveCommentsError)
    with pytest.raises(BehaveCommentsError):
        raise exc_class(*args)


def test_content_type_error_attrs() -> None:
    e = ContentTypeError("xml")
    assert e.content_type == "xml"
    assert "xml" in str(e)


def test_parse_error_attrs() -> None:
    e = ParseError("json", "Expecting value", 3)
    assert e.content_type == "json"
    assert e.detail == "Expecting value"
    assert e.line == 3
    assert "json" in str(e)
    assert "Expecting value" in str(e)
    assert "line 3" in str(e)


def test_parse_error_line_none() -> None:
    e = ParseError("json", "Unexpected EOF")
    assert e.line is None
    assert "line" not in str(e)


def test_annotation_parse_error_attrs() -> None:
    e = AnnotationParseError(5, "# @key")
    assert e.line == 5
    assert e.raw == "# @key"
    assert "line 5" in str(e)
    assert "# @key" in str(e)


def test_lifecycle_step_error_attrs() -> None:
    e = LifecycleStepError("before-feature", "Given the db", "Step not found")
    assert e.hook_type == "before-feature"
    assert e.step_text == "Given the db"
    assert e.detail == "Step not found"
    assert "before-feature" in str(e)
    assert "Given the db" in str(e)
    assert "Step not found" in str(e)


def test_catchable_by_specific_type() -> None:
    with pytest.raises(ParseError) as exc_info:
        raise ParseError("json", "Expecting value", 3)
    assert exc_info.value.line == 3


# ---------------------------------------------------------------------------
# Edge cases: string representation, catchable patterns
# ---------------------------------------------------------------------------


def test_content_type_error_str() -> None:
    e = ContentTypeError("xml")
    s = str(e)
    assert "xml" in s
    assert "Unsupported content type" in s


def test_parse_error_str_with_line() -> None:
    e = ParseError("json", "Expecting value", 3)
    s = str(e)
    assert "json" in s
    assert "Expecting value" in s
    assert "line 3" in s


def test_parse_error_str_without_line() -> None:
    e = ParseError("json", "Unexpected EOF")
    s = str(e)
    assert "json" in s
    assert "Unexpected EOF" in s
    assert "line" not in s


def test_annotation_parse_error_str() -> None:
    e = AnnotationParseError(5, "# @key")
    s = str(e)
    assert "line 5" in s
    assert "# @key" in s


def test_lifecycle_step_error_str() -> None:
    e = LifecycleStepError("before-feature", "Given the db", "Step not found")
    s = str(e)
    assert "before-feature" in s
    assert "Given the db" in s
    assert "Step not found" in s


def test_all_errors_catchable_by_base() -> None:
    for exc_class, args in [
        (ContentTypeError, ("xml",)),
        (ParseError, ("json", "error")),
        (AnnotationParseError, (1, "# @bad")),
        (LifecycleStepError, ("before-feature", "Given x", "fail")),
    ]:
        try:
            raise exc_class(*args)
        except BehaveCommentsError:
            pass
        else:
            pytest.fail(f"{exc_class.__name__} not catchable by BehaveCommentsError")


def test_parse_error_catchable_by_parse_error() -> None:
    with pytest.raises(ParseError):
        raise ParseError("json", "error", 1)


def test_content_type_error_catchable_by_content_type_error() -> None:
    with pytest.raises(ContentTypeError):
        raise ContentTypeError("unknown")


def test_annotation_parse_error_catchable_by_annotation_parse_error() -> None:
    with pytest.raises(AnnotationParseError):
        raise AnnotationParseError(1, "# @bad")


def test_lifecycle_step_error_catchable_by_lifecycle_step_error() -> None:
    with pytest.raises(LifecycleStepError):
        raise LifecycleStepError("before-feature", "Given x", "fail")


def test_parse_error_with_line_zero() -> None:
    e = ParseError("json", "error", 0)
    assert e.line == 0
    assert "line 0" in str(e)


def test_parse_error_with_negative_line() -> None:
    e = ParseError("json", "error", -1)
    assert e.line == -1
    assert "line -1" in str(e)


def test_lifecycle_step_error_empty_hook_type() -> None:
    e = LifecycleStepError("", "Given x", "fail")
    assert e.hook_type == ""
    assert e.step_text == "Given x"
    assert e.detail == "fail"


def test_lifecycle_step_error_empty_step_text() -> None:
    e = LifecycleStepError("before-feature", "", "fail")
    assert e.hook_type == "before-feature"
    assert e.step_text == ""
