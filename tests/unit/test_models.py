"""Tests for behave-comments data models."""

from __future__ import annotations

import dataclasses

import pytest

from behave_comments.models import Annotation, TextBlock


def test_text_block_frozen() -> None:
    tb = TextBlock(content="x", content_type="text/plain", line=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        tb.content = "y"  # type: ignore[misc]


def test_text_block_slots() -> None:
    tb = TextBlock(content="x", content_type="text/plain", line=1)
    with pytest.raises((AttributeError, TypeError)):
        tb.new_attr = 1  # type: ignore[attr-defined]


def test_text_block_no_dict() -> None:
    tb = TextBlock(content="x", content_type="text/plain", line=1)
    assert not hasattr(tb, "__dict__")


def test_text_block_default_parsed_is_none() -> None:
    tb = TextBlock(content="x", content_type="text/plain", line=1)
    assert tb.parsed is None


def test_text_block_with_parsed() -> None:
    tb = TextBlock(content="x", content_type="json", line=1, parsed={"key": "value"})
    assert tb.parsed == {"key": "value"}


def test_text_block_eq() -> None:
    a = TextBlock(content="x", content_type="text/plain", line=1)
    b = TextBlock(content="x", content_type="text/plain", line=1)
    assert a == b


def test_text_block_ne() -> None:
    a = TextBlock(content="x", content_type="text/plain", line=1)
    b = TextBlock(content="y", content_type="text/plain", line=1)
    assert a != b


def test_text_block_repr() -> None:
    tb = TextBlock(content="x", content_type="text/plain", line=1)
    r = repr(tb)
    assert "TextBlock" in r
    assert "content='x'" in r
    assert "content_type='text/plain'" in r
    assert "line=1" in r
    assert "parsed=None" in r


def test_annotation_frozen() -> None:
    ann = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    with pytest.raises(dataclasses.FrozenInstanceError):
        ann.key = "x"  # type: ignore[misc]


def test_annotation_slots() -> None:
    ann = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    with pytest.raises((AttributeError, TypeError)):
        ann.new_attr = 1  # type: ignore[attr-defined]


def test_annotation_no_dict() -> None:
    ann = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    assert not hasattr(ann, "__dict__")


def test_annotation_eq() -> None:
    a = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    b = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    assert a == b


def test_annotation_repr() -> None:
    ann = Annotation(key="jira", value="TICKET-42", line=5, scope="feature", scope_name="Login")
    r = repr(ann)
    assert "Annotation" in r
    assert "key='jira'" in r
    assert "value='TICKET-42'" in r
    assert "line=5" in r
    assert "scope='feature'" in r
    assert "scope_name='Login'" in r
