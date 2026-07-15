"""Tests for behave-comments parser."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

from behave_comments.errors import ContentTypeError, MissingDependencyError, ParseError
from behave_comments.parser import (
    SUPPORTED_CONTENT_TYPES,
    _parse_csv,
    _parse_form_urlencoded,
    _parse_graphql,
    _parse_json,
    _parse_text_plain,
    _parse_xml,
    _parse_yaml,
    detect_content_type,
    extract_text_block,
    parse_text,
)
from tests.conftest import FakeStep


@pytest.mark.parametrize(
    ("opening_line", "expected"),
    [
        ('"""json', "json"),
        ('"""yaml', "yaml"),
        ('"""xml', "xml"),
        ('"""csv', "csv"),
        ('"""form-urlencoded', "form-urlencoded"),
        ('"""graphql', "graphql"),
        ('"""text/plain', "text/plain"),
        ('"""', "text/plain"),
        ('"""  json  ', "json"),
        ('"""  ', "text/plain"),
        ('"""JSON', "json"),
        ('"""YAML', "yaml"),
        ('"""json\n', "json"),
    ],
)
def test_detect_content_type_valid(opening_line: str, expected: str) -> None:
    assert detect_content_type(opening_line) == expected


@pytest.mark.parametrize(
    ("opening_line", "expected_in_error"),
    [
        ('"""unknown', "unknown"),
        ('"""json extra', '"""json extra'),
        ("not triple quotes", "not triple quotes"),
        ("", ""),
    ],
)
def test_detect_content_type_invalid(opening_line: str, expected_in_error: str) -> None:
    with pytest.raises(ContentTypeError) as exc_info:
        detect_content_type(opening_line)
    assert exc_info.value.content_type == expected_in_error


def test_supported_content_types_is_frozenset() -> None:
    assert isinstance(SUPPORTED_CONTENT_TYPES, frozenset)
    assert "text/plain" in SUPPORTED_CONTENT_TYPES
    assert "json" in SUPPORTED_CONTENT_TYPES
    assert "form-urlencoded" in SUPPORTED_CONTENT_TYPES


@pytest.mark.parametrize(
    "text",
    [
        "hello world",
        "",
        "line1\nline2\nline3",
        "café — naïve",
        "col1\tcol2",
    ],
)
def test_parse_text_plain(text: str) -> None:
    assert _parse_text_plain(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "query { user { name } }",
        "fragment UserFields on User { name email } query { user { ...UserFields } }",
        "",
        "query GetUser($id: ID!) { user(id: $id) { name } }",
    ],
)
def test_parse_graphql(text: str) -> None:
    assert _parse_graphql(text) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"key": "value"}', {"key": "value"}),
        ("[1, 2, 3]", [1, 2, 3]),
        ('{"a": {"b": [1, 2]}}', {"a": {"b": [1, 2]}}),
        ('"hello"', "hello"),
        ("42", 42),
        ("true", True),
        ("null", None),
        ("{}", {}),
        ("[]", []),
    ],
)
def test_parse_json_valid(text: str, expected: object) -> None:
    assert _parse_json(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "{key: value}",
        '{"unclosed":',
        '{"a": 1,}',
    ],
)
def test_parse_json_invalid(text: str) -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_json(text)
    assert exc_info.value.content_type == "json"
    assert exc_info.value.line is not None
    assert exc_info.value.detail != ""


def test_parse_json_error_line_matches_lineno() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_json("")
    try:
        json.loads("")
    except json.JSONDecodeError as e:
        assert exc_info.value.line == e.lineno


def test_parse_json_error_detail_contains_original_message() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_json("")
    try:
        json.loads("")
    except json.JSONDecodeError as e:
        assert str(e) in exc_info.value.detail


def test_parse_json_error_chained_cause() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_json("")
    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "name,age\nAlice,30\nBob,25",
            [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}],
        ),
        ("name,age\nAlice,30", [{"name": "Alice", "age": "30"}]),
        ('"name, inc",value\n"Acme Corp",42', {"name, inc": "Acme Corp", "value": "42"}),
        ("", []),
        ("name,age", []),
        (" name , age \nAlice,30", {" name ": "Alice", " age ": "30"}),
        ("a,b\n1,2\n3,4", [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]),
    ],
)
def test_parse_csv(text: str, expected: object) -> None:
    result = _parse_csv(text)
    if isinstance(expected, list):
        assert result == expected
    else:
        assert result[0] == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("key=value&key2=value2", {"key": ["value"], "key2": ["value2"]}),
        ("key=value1&key=value2", {"key": ["value1", "value2"]}),
        ("name=John%20Doe", {"name": ["John Doe"]}),
        ("", {}),
        ("key=", {"key": [""]}),
        ("q=hello+world", {"q": ["hello world"]}),
        ("key", {"key": [""]}),
    ],
)
def test_parse_form_urlencoded(text: str, expected: dict[str, list[str]]) -> None:
    assert _parse_form_urlencoded(text) == expected


def test_parse_xml_basic() -> None:
    root = _parse_xml("<root><child>text</child></root>")
    assert root.tag == "root"
    assert root.find("child").text == "text"


def test_parse_xml_with_attributes() -> None:
    root = _parse_xml('<root attr="value"/>')
    assert root.tag == "root"
    assert root.attrib == {"attr": "value"}


def test_parse_xml_with_namespace() -> None:
    root = _parse_xml("<ns:root xmlns:ns='http://example.com'/>")
    assert root.tag == "{http://example.com}root"


def test_parse_xml_with_declaration() -> None:
    root = _parse_xml('<?xml version="1.0"?><root/>')
    assert root.tag == "root"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "<root><unclosed>",
    ],
)
def test_parse_xml_invalid(text: str) -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_xml(text)
    assert exc_info.value.content_type == "xml"


def test_parse_xml_error_chained_cause() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_xml("")
    assert isinstance(exc_info.value.__cause__, ET.ParseError)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("key: value", {"key": "value"}),
        ("- item1\n- item2", ["item1", "item2"]),
        ("outer:\n  inner: value", {"outer": {"inner": "value"}}),
        ("", None),
        ("   ", None),
        ("key: 42", {"key": 42}),
        ("key: 3.14", {"key": 3.14}),
        ("key: true", {"key": True}),
        ("key: null", {"key": None}),
        ("key: ~", {"key": None}),
        ("key: value\n# comment", {"key": "value"}),
        ("---\nkey: value", {"key": "value"}),
    ],
)
def test_parse_yaml_valid(text: str, expected: object) -> None:
    assert _parse_yaml(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "key: value: extra",
        ":\n  - ",
    ],
)
def test_parse_yaml_invalid(text: str) -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_yaml(text)
    assert exc_info.value.content_type == "yaml"


def test_parse_yaml_error_chained_cause() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_yaml("key: value: extra")
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)


def test_parse_yaml_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "yaml", None)
    with pytest.raises(MissingDependencyError) as exc_info:
        _parse_yaml("key: value")
    assert exc_info.value.dependency == "pyyaml"
    assert exc_info.value.extra == "yaml"
    assert "pip install behave-comments[yaml]" in str(exc_info.value)


@pytest.mark.parametrize(
    ("text", "content_type", "expected"),
    [
        ('{"k": "v"}', "json", {"k": "v"}),
        ("key: value", "yaml", {"key": "value"}),
        ("name,age\nAlice,30", "csv", [{"name": "Alice", "age": "30"}]),
        ("key=value", "form-urlencoded", {"key": ["value"]}),
        ("query { x }", "graphql", "query { x }"),
        ("hello", "text/plain", "hello"),
        ("hello", None, "hello"),
    ],
)
def test_parse_text_dispatch(text: str, content_type: str | None, expected: object) -> None:
    if content_type is None:
        assert parse_text(text) == expected
    else:
        assert parse_text(text, content_type) == expected


def test_parse_text_xml_dispatch() -> None:
    root = parse_text("<root/>", "xml")
    assert root.tag == "root"


@pytest.mark.parametrize(
    ("text", "content_type"),
    [
        ('{"k": "v"}', "JSON"),
        ('{"k": "v"}', "Json"),
        ('{"k": "v"}', "  json  "),
    ],
)
def test_parse_text_case_insensitive(text: str, content_type: str) -> None:
    assert parse_text(text, content_type) == {"k": "v"}


@pytest.mark.parametrize(
    ("text", "content_type"),
    [
        ("hello", "unknown"),
        ("hello", ""),
    ],
)
def test_parse_text_content_type_error(text: str, content_type: str) -> None:
    with pytest.raises(ContentTypeError):
        parse_text(text, content_type)


def test_parse_text_json_parse_error() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_text("", "json")
    assert exc_info.value.content_type == "json"


def test_parse_text_yaml_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "yaml", None)
    with pytest.raises(MissingDependencyError):
        parse_text("key: value", "yaml")


def test_parse_text_no_double_wrap() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_text("{bad json", "json")
    assert exc_info.value.content_type == "json"
    assert not isinstance(exc_info.value.__cause__, ParseError)


def test_parse_text_yaml_parse_error() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_text("bad: yaml: extra", "yaml")
    assert exc_info.value.content_type == "yaml"


@pytest.mark.parametrize(
    ("text", "expected_content_type", "expected_content", "expected_parsed"),
    [
        ('json\n{"key": "value"}', "json", '{"key": "value"}', {"key": "value"}),
        ("yaml\nkey: value", "yaml", "key: value", {"key": "value"}),
        ("csv\nname,age\nAlice,30", "csv", "name,age\nAlice,30", [{"name": "Alice", "age": "30"}]),
        ("graphql\nquery { x }", "graphql", "query { x }", "query { x }"),
        ("form-urlencoded\nkey=value", "form-urlencoded", "key=value", {"key": ["value"]}),
        ("text/plain\nhello", "text/plain", "hello", "hello"),
    ],
)
def test_extract_text_block_with_content_type(
    text: str,
    expected_content_type: str,
    expected_content: str,
    expected_parsed: object,
) -> None:
    step = FakeStep(text=text)
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == expected_content_type
    assert tb.content == expected_content
    assert tb.parsed == expected_parsed


def test_extract_text_block_xml() -> None:
    step = FakeStep(text="xml\n<root/>")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "xml"
    assert tb.parsed.tag == "root"


@pytest.mark.parametrize(
    ("text", "expected_content", "expected_parsed"),
    [
        ("just text", "just text", "just text"),
        ("line1\nline2", "line1\nline2", "line1\nline2"),
    ],
)
def test_extract_text_block_without_content_type(
    text: str, expected_content: str, expected_parsed: str
) -> None:
    step = FakeStep(text=text)
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == expected_content
    assert tb.parsed == expected_parsed


@pytest.mark.parametrize(
    "step",
    [
        FakeStep(text=None),
        FakeStep(text=""),
        FakeStep(),
    ],
)
def test_extract_text_block_none_or_empty(step: FakeStep) -> None:
    assert extract_text_block(step) is None


def test_extract_text_block_json_colon_not_content_type() -> None:
    step = FakeStep(text="json:\n  key: value")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "json:\n  key: value"


def test_extract_text_block_single_line_json_is_content() -> None:
    step = FakeStep(text="json")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "json"
    assert tb.parsed == "json"


def test_extract_text_block_case_insensitive() -> None:
    step = FakeStep(text='JSON\n{"k": "v"}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "json"
    assert tb.parsed == {"k": "v"}


def test_extract_text_block_whitespace_stripped() -> None:
    step = FakeStep(text='  json  \n{"k": "v"}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "json"
    assert tb.parsed == {"k": "v"}


def test_extract_text_block_empty_json_content_raises() -> None:
    step = FakeStep(text="json\n")
    with pytest.raises(ParseError) as exc_info:
        extract_text_block(step)
    assert exc_info.value.content_type == "json"


def test_extract_text_block_unknown_type_is_text_plain() -> None:
    step = FakeStep(text="unknown\nhello")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "unknown\nhello"


def test_extract_text_block_line_from_step() -> None:
    step = FakeStep(text='json\n{"k": "v"}', line=42)
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.line == 42


def test_extract_text_block_default_line() -> None:
    step = FakeStep(text='json\n{"k": "v"}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.line == 0
