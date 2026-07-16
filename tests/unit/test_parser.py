"""Tests for behave-comments parser."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest
import yaml

from behave_comments.errors import ContentTypeError, ParseError
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


def test_parse_yaml_error_line_is_one_indexed() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_yaml("valid: line\ninvalid: [")
    assert exc_info.value.line is not None
    assert exc_info.value.line >= 1


def test_parse_yaml_error_line_for_first_line() -> None:
    with pytest.raises(ParseError) as exc_info:
        _parse_yaml("key: value: extra: more")
    assert exc_info.value.line is not None
    assert exc_info.value.line >= 1


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


# ---------------------------------------------------------------------------
# Edge cases: parser error paths and unusual inputs
# ---------------------------------------------------------------------------


def test_parse_csv_with_field_size_limit_error(monkeypatch) -> None:
    import csv as csv_module

    original_limit = csv_module.field_size_limit

    def tiny_field_limit(*args, **kwargs):
        raise csv_module.Error("field size limit exceeded")

    monkeypatch.setattr(csv_module, "field_size_limit", lambda: 1)
    monkeypatch.setattr(
        csv_module,
        "DictReader",
        lambda *a, **kw: (_ for _ in ()).throw(
            csv_module.Error("line contains null byte")
        ),
    )
    with pytest.raises(ParseError) as exc_info:
        _parse_csv("name,age\nAlice,30")
    assert exc_info.value.content_type == "csv"
    monkeypatch.setattr(csv_module, "field_size_limit", lambda: original_limit)


def test_parse_csv_empty_content() -> None:
    result = _parse_csv("")
    assert result == []


def test_parse_csv_only_header() -> None:
    result = _parse_csv("name,age\n")
    assert result == []


def test_parse_csv_multiple_rows() -> None:
    result = _parse_csv("name,age\nAlice,30\nBob,25\nCharlie,35\n")
    assert len(result) == 3
    assert result[0]["name"] == "Alice"
    assert result[1]["name"] == "Bob"
    assert result[2]["name"] == "Charlie"


def test_parse_csv_with_quoted_fields() -> None:
    result = _parse_csv('name,desc\n"Alice","Hello, world"\n')
    assert len(result) == 1
    assert result[0]["name"] == "Alice"
    assert result[0]["desc"] == "Hello, world"


def test_parse_xml_with_namespaces() -> None:
    xml_text = (
        '<root xmlns:ns="http://example.com">'
        "<ns:child>value</ns:child>"
        "</root>"
    )
    root = _parse_xml(xml_text)
    assert root.tag == "root"
    child = root.find("{http://example.com}child")
    assert child is not None
    assert child.text == "value"


def test_parse_xml_with_attributes() -> None:
    xml_text = '<root id="42" status="active"><item>text</item></root>'
    root = _parse_xml(xml_text)
    assert root.get("id") == "42"
    assert root.get("status") == "active"


def test_parse_form_urlencoded_multiple_values() -> None:
    result = _parse_form_urlencoded("a=1&b=2&c=3")
    assert result == {"a": ["1"], "b": ["2"], "c": ["3"]}


def test_parse_form_urlencoded_with_special_chars() -> None:
    result = _parse_form_urlencoded("name=John+Doe&email=test%40example.com")
    assert result["name"] == ["John Doe"]
    assert result["email"] == ["test@example.com"]


def test_parse_form_urlencoded_empty_value() -> None:
    result = _parse_form_urlencoded("key=&other=value")
    assert result["key"] == [""]
    assert result["other"] == ["value"]


def test_parse_graphql_with_variables() -> None:
    query = "query GetUser($id: ID!) { user(id: $id) { name } }"
    result = _parse_graphql(query)
    assert result == query


def test_parse_graphql_mutation() -> None:
    query = "mutation CreateUser($name: String!) { createUser(name: $name) { id } }"
    result = _parse_graphql(query)
    assert result == query


def test_parse_text_plain_with_unicode() -> None:
    result = _parse_text_plain("Hello — café — naïve — 日本語")
    assert result == "Hello — café — naïve — 日本語"


def test_parse_text_plain_empty() -> None:
    result = _parse_text_plain("")
    assert result == ""


def test_parse_text_plain_multiline() -> None:
    result = _parse_text_plain("line1\nline2\nline3")
    assert result == "line1\nline2\nline3"


def test_detect_content_type_json_array() -> None:
    assert detect_content_type('"""json') == "json"


def test_detect_content_type_json_nested_object() -> None:
    assert detect_content_type('"""json') == "json"


def test_detect_content_type_yaml_with_list() -> None:
    assert detect_content_type('"""yaml') == "yaml"


def test_detect_content_type_xml_with_declaration() -> None:
    assert detect_content_type('"""xml') == "xml"


def test_detect_content_type_case_mixed() -> None:
    assert detect_content_type('"""JSON') == "json"
    assert detect_content_type('"""YAML') == "yaml"
    assert detect_content_type('"""XML') == "xml"
    assert detect_content_type('"""CSV') == "csv"


def test_extract_text_block_json_array() -> None:
    step = FakeStep(text='json\n[1, 2, 3]')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "json"
    assert tb.parsed == [1, 2, 3]


def test_extract_text_block_yaml_list() -> None:
    step = FakeStep(text="yaml\n- item1\n- item2")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "yaml"
    assert tb.parsed == ["item1", "item2"]


def test_extract_text_block_xml_with_declaration() -> None:
    step = FakeStep(text='xml\n<?xml version="1.0"?><root><child>text</child></root>')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "xml"
    assert tb.parsed.tag == "root"


def test_extract_text_block_csv_with_multiple_rows() -> None:
    step = FakeStep(text="csv\nname,age\nAlice,30\nBob,25")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "csv"
    assert len(tb.parsed) == 2
    assert tb.parsed[0]["name"] == "Alice"
    assert tb.parsed[1]["name"] == "Bob"


def test_extract_text_block_form_urlencoded_special_chars() -> None:
    step = FakeStep(text="form-urlencoded\nname=John+Doe&email=test%40example.com")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "form-urlencoded"
    assert tb.parsed["name"] == ["John Doe"]
    assert tb.parsed["email"] == ["test@example.com"]


def test_extract_text_block_graphql_mutation() -> None:
    step = FakeStep(
        text="graphql\nmutation CreateUser($name: String!) { createUser(name: $name) { id } }"
    )
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "graphql"
    assert "mutation" in tb.parsed


def test_extract_text_block_text_plain_unicode() -> None:
    step = FakeStep(text="text/plain\nHello — café — 日本語")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.parsed == "Hello — café — 日本語"


# ---------------------------------------------------------------------------
# Edge cases: parse_text dispatch, extract_text_block edge cases
# ---------------------------------------------------------------------------


def test_parse_text_xml_dispatch() -> None:
    root = parse_text("<root><child>text</child></root>", "xml")
    assert root.tag == "root"
    assert root.find("child").text == "text"


def test_parse_text_csv_dispatch() -> None:
    result = parse_text("name,age\nAlice,30", "csv")
    assert result == [{"name": "Alice", "age": "30"}]


def test_parse_text_form_urlencoded_dispatch() -> None:
    result = parse_text("key=value&other=2", "form-urlencoded")
    assert result == {"key": ["value"], "other": ["2"]}


def test_parse_text_graphql_dispatch() -> None:
    result = parse_text("query { x }", "graphql")
    assert result == "query { x }"


def test_parse_text_text_plain_dispatch() -> None:
    result = parse_text("hello world", "text/plain")
    assert result == "hello world"


def test_parse_text_empty_string_text_plain() -> None:
    assert parse_text("", "text/plain") == ""


def test_parse_text_empty_string_graphql() -> None:
    assert parse_text("", "graphql") == ""


def test_parse_text_with_whitespace_content_type() -> None:
    assert parse_text('{"k": "v"}', "  json  ") == {"k": "v"}


def test_parse_text_with_uppercase_content_type() -> None:
    assert parse_text('{"k": "v"}', "JSON") == {"k": "v"}


def test_parse_text_with_mixed_case_content_type() -> None:
    assert parse_text('{"k": "v"}', "Json") == {"k": "v"}


def test_extract_text_block_step_without_line_attr() -> None:
    class StepNoLine:
        text = 'json\n{"k": "v"}'

    tb = extract_text_block(StepNoLine())
    assert tb is not None
    assert tb.line == 0


def test_extract_text_block_content_type_only_no_body() -> None:
    step = FakeStep(text="json")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "json"


def test_extract_text_block_yaml_empty_body() -> None:
    step = FakeStep(text="yaml\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "yaml"
    assert tb.parsed is None


def test_extract_text_block_csv_empty_body() -> None:
    step = FakeStep(text="csv\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "csv"
    assert tb.parsed == []


def test_extract_text_block_xml_empty_body_raises() -> None:
    step = FakeStep(text="xml\n")
    with pytest.raises(ParseError):
        extract_text_block(step)


def test_extract_text_block_form_urlencoded_empty_body() -> None:
    step = FakeStep(text="form-urlencoded\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "form-urlencoded"
    assert tb.parsed == {}


def test_extract_text_block_graphql_empty_body() -> None:
    step = FakeStep(text="graphql\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "graphql"
    assert tb.parsed == ""


def test_extract_text_block_text_plain_empty_body() -> None:
    step = FakeStep(text="text/plain\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.parsed == ""


def test_extract_text_block_content_type_case_insensitive() -> None:
    step = FakeStep(text='JSON\n{"k": "v"}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "json"
    assert tb.parsed == {"k": "v"}


def test_extract_text_block_content_type_with_whitespace() -> None:
    step = FakeStep(text='  json  \n{"k": "v"}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "json"
    assert tb.parsed == {"k": "v"}


def test_extract_text_block_multiline_json() -> None:
    step = FakeStep(text='json\n{\n  "key": "value",\n  "num": 42\n}')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.parsed == {"key": "value", "num": 42}


def test_extract_text_block_multiline_yaml() -> None:
    step = FakeStep(text="yaml\nouter:\n  inner: value")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.parsed == {"outer": {"inner": "value"}}


def test_extract_text_block_multiline_csv() -> None:
    step = FakeStep(text="csv\nname,age\nAlice,30\nBob,25")
    tb = extract_text_block(step)
    assert tb is not None
    assert len(tb.parsed) == 2


def test_extract_text_block_multiline_xml() -> None:
    step = FakeStep(text="xml\n<root>\n  <child>text</child>\n</root>")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.parsed.tag == "root"
    assert tb.parsed.find("child").text == "text"


def test_extract_text_block_multiline_form_urlencoded() -> None:
    step = FakeStep(text="form-urlencoded\nkey=value&other=2")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.parsed == {"key": ["value"], "other": ["2"]}


def test_extract_text_block_multiline_graphql() -> None:
    step = FakeStep(text="graphql\nquery {\n  user {\n    name\n  }\n}")
    tb = extract_text_block(step)
    assert tb is not None
    assert "query" in tb.parsed
    assert "user" in tb.parsed


def test_extract_text_block_multiline_text_plain() -> None:
    step = FakeStep(text="text/plain\nline1\nline2\nline3")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.parsed == "line1\nline2\nline3"


def test_extract_text_block_content_type_only_no_body() -> None:
    step = FakeStep(text="yaml\n")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "yaml"
    assert tb.content == ""
    assert tb.parsed is None


def test_extract_text_block_content_type_only_text_plain() -> None:
    step = FakeStep(text="text/plain")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "text/plain"
    assert tb.parsed == "text/plain"


def test_parse_text_none_content_type_raises_content_type_error() -> None:
    with pytest.raises(ContentTypeError):
        parse_text("data", None)  # type: ignore[arg-type]


def test_parse_text_uppercase_content_type() -> None:
    result = parse_text('{"key": "value"}', "JSON")
    assert result == {"key": "value"}


def test_parse_text_content_type_with_spaces() -> None:
    result = parse_text('{"key": "value"}', "  JSON  ")
    assert result == {"key": "value"}


def test_extract_text_block_single_word_content_type() -> None:
    step = FakeStep(text="yaml")
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "text/plain"
    assert tb.content == "yaml"
    assert tb.parsed == "yaml"


def test_parse_csv_empty_input() -> None:
    result = parse_text("", "csv")
    assert result == []


def test_parse_csv_header_only() -> None:
    result = parse_text("name,age", "csv")
    assert result == []


def test_parse_form_urlencoded_empty_input() -> None:
    result = parse_text("", "form-urlencoded")
    assert result == {}


def test_parse_form_urlencoded_blank_values() -> None:
    result = parse_text("key1=&key2=val2", "form-urlencoded")
    assert result == {"key1": [""], "key2": ["val2"]}


def test_detect_content_type_uppercase() -> None:
    assert detect_content_type('"""JSON') == "json"
    assert detect_content_type('"""YAML') == "yaml"
    assert detect_content_type('"""XML') == "xml"


def test_detect_content_type_with_trailing_spaces() -> None:
    assert detect_content_type('"""  yaml  ') == "yaml"


def test_parse_xml_with_encoding_declaration() -> None:
    xml = '<?xml version="1.0" encoding="UTF-8"?><root><item>1</item></root>'
    result = parse_text(xml, "xml")
    assert result.tag == "root"
    assert result[0].tag == "item"
    assert result[0].text == "1"


def test_parse_yaml_empty_string_returns_none() -> None:
    result = parse_text("", "yaml")
    assert result is None


def test_parse_yaml_whitespace_only_returns_none() -> None:
    result = parse_text("   \n  \n", "yaml")
    assert result is None


def test_parse_yaml_list() -> None:
    result = parse_text("- a\n- b\n- c", "yaml")
    assert result == ["a", "b", "c"]


def test_parse_yaml_scalar() -> None:
    result = parse_text("42", "yaml")
    assert result == 42


def test_extract_text_block_xml_with_namespaces() -> None:
    step = FakeStep(text='xml\n<root xmlns:ns="http://example.com"><ns:child>x</ns:child></root>')
    tb = extract_text_block(step)
    assert tb is not None
    assert tb.content_type == "xml"
    root = tb.parsed
    assert root.tag == "root"
    assert len(root) == 1


def test_parse_text_xml_with_attributes() -> None:
    result = parse_text('<root attr="value">text</root>', "xml")
    assert result.tag == "root"
    assert result.get("attr") == "value"
    assert result.text == "text"


def test_parse_text_csv_with_quoted_fields() -> None:
    csv_text = 'name,desc\n"Alice","Hello, World"\n"Bob","He said ""hi"""'
    result = parse_text(csv_text, "csv")
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["desc"] == "Hello, World"
    assert result[1]["desc"] == 'He said "hi"'


def test_parse_text_form_urlencoded_multiple_values() -> None:
    result = parse_text("key=val1&key=val2", "form-urlencoded")
    assert result == {"key": ["val1", "val2"]}


def test_parse_text_form_urlencoded_url_encoded() -> None:
    result = parse_text("name=John%20Doe&city=New%20York", "form-urlencoded")
    assert result == {"name": ["John Doe"], "city": ["New York"]}


def test_parse_csv_with_missing_fields() -> None:
    csv_text = "name,age,city\nAlice,30\nBob,25,NYC"
    result = parse_text(csv_text, "csv")
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == "30"
    assert "city" not in result[0]
    assert result[1]["city"] == "NYC"


def test_parse_text_empty_string_content_type() -> None:
    with pytest.raises(ContentTypeError):
        parse_text("data", "")


def test_detect_content_type_empty_string() -> None:
    with pytest.raises(ContentTypeError):
        detect_content_type("")


def test_detect_content_type_just_triple_quotes() -> None:
    assert detect_content_type('"""') == "text/plain"


def test_detect_content_type_triple_quotes_with_spaces() -> None:
    assert detect_content_type('"""   ') == "text/plain"


def test_parse_json_nested() -> None:
    result = parse_text('{"a": {"b": [1, 2, {"c": true}]}}', "json")
    assert result["a"]["b"][2]["c"] is True


def test_parse_json_empty_object() -> None:
    assert parse_text("{}", "json") == {}


def test_parse_json_empty_array() -> None:
    assert parse_text("[]", "json") == []


def test_parse_json_null_value() -> None:
    assert parse_text("null", "json") is None


def test_parse_yaml_nested() -> None:
    result = parse_text("outer:\n  inner:\n    deep: value", "yaml")
    assert result["outer"]["inner"]["deep"] == "value"


def test_parse_yaml_null() -> None:
    assert parse_text("null", "yaml") is None


def test_parse_yaml_boolean() -> None:
    assert parse_text("true", "yaml") is True
    assert parse_text("false", "yaml") is False
