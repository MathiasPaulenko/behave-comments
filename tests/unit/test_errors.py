"""Tests for the behave-comments exception hierarchy."""

from __future__ import annotations

import pytest

from behave_comments.errors import (
    AnnotationParseError,
    BehaveCommentsError,
    ContentTypeError,
    LifecycleStepError,
    MissingDependencyError,
    ParseError,
)


@pytest.mark.parametrize(
    ("exc_class", "args"),
    [
        (ContentTypeError, ("xml",)),
        (ParseError, ("json", "Expecting value", 3)),
        (MissingDependencyError, ("pyyaml", "yaml")),
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


def test_missing_dependency_error_attrs() -> None:
    e = MissingDependencyError("pyyaml", "yaml")
    assert e.dependency == "pyyaml"
    assert e.extra == "yaml"
    assert "pip install behave-comments[yaml]" in str(e)


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
