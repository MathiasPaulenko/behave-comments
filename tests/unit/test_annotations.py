"""Tests for behave-comments annotations."""

from __future__ import annotations

import pytest

from behave_comments.annotations import (
    annotations_to_tags,
    extract_annotations,
    inject_metadata,
    parse_annotation_line,
)
from behave_comments.errors import AnnotationParseError
from behave_comments.models import Annotation
from tests.conftest import FakeContext, FakeFeature


@pytest.mark.parametrize(
    ("line", "expected_key", "expected_value"),
    [
        ("# @jira TICKET-42", "jira", "TICKET-42"),
        ("# @jira: TICKET-42", "jira", "TICKET-42"),
        ("# @jira=TICKET-42", "jira", "TICKET-42"),
        ("# @priority high", "priority", "high"),
        ("# @owner team-alpha", "owner", "team-alpha"),
    ],
)
def test_parse_annotation_line_valid_syntax(
    line: str, expected_key: str, expected_value: str
) -> None:
    ann = parse_annotation_line(line, 1)
    assert ann is not None
    assert ann.key == expected_key
    assert ann.value == expected_value


@pytest.mark.parametrize(
    ("line", "expected_key", "expected_value"),
    [
        ("#  @jira  TICKET-42  ", "jira", "TICKET-42"),
        ("# @jira   TICKET-42   ", "jira", "TICKET-42"),
        ("#\t@jira\tTICKET-42", "jira", "TICKET-42"),
    ],
)
def test_parse_annotation_line_whitespace(
    line: str, expected_key: str, expected_value: str
) -> None:
    ann = parse_annotation_line(line, 1)
    assert ann is not None
    assert ann.key == expected_key
    assert ann.value == expected_value


@pytest.mark.parametrize(
    ("line", "expected_key", "expected_value"),
    [
        ("# @issue-id PRJ-123", "issue-id", "PRJ-123"),
        ("# @test-case TC-001", "test-case", "TC-001"),
    ],
)
def test_parse_annotation_line_hyphenated_keys(
    line: str, expected_key: str, expected_value: str
) -> None:
    ann = parse_annotation_line(line, 1)
    assert ann is not None
    assert ann.key == expected_key
    assert ann.value == expected_value


@pytest.mark.parametrize(
    ("line", "expected_key", "expected_value"),
    [
        ("# @key", "key", ""),
        ("# @key:", "key", ""),
        ("# @key=", "key", ""),
        ("# @key value with spaces", "key", "value with spaces"),
        ("# @key value: with: colons", "key", "value: with: colons"),
    ],
)
def test_parse_annotation_line_special_values(
    line: str, expected_key: str, expected_value: str
) -> None:
    ann = parse_annotation_line(line, 1)
    assert ann is not None
    assert ann.key == expected_key
    assert ann.value == expected_value


@pytest.mark.parametrize(
    "line",
    [
        "# This is a regular comment",
        "# Regular comment with @ symbol",
        "Given a step",
        "",
        "   ",
    ],
)
def test_parse_annotation_line_not_annotation(line: str) -> None:
    assert parse_annotation_line(line, 1) is None


@pytest.mark.parametrize(
    "line",
    [
        "# @",
        "# @!invalid",
        "# @  spaces",
    ],
)
def test_parse_annotation_line_error(line: str) -> None:
    with pytest.raises(AnnotationParseError) as exc_info:
        parse_annotation_line(line, 42)
    assert exc_info.value.line == 42
    assert exc_info.value.raw == line.strip()


def test_parse_annotation_line_line_number() -> None:
    ann = parse_annotation_line("# @jira TICKET-42", 99)
    assert ann is not None
    assert ann.line == 99


def test_parse_annotation_line_scope_defaults() -> None:
    ann = parse_annotation_line("# @jira TICKET-42", 1)
    assert ann is not None
    assert ann.scope == ""
    assert ann.scope_name == ""


def test_parse_annotation_line_returns_annotation_instance() -> None:
    ann = parse_annotation_line("# @jira TICKET-42", 1)
    assert ann is not None
    assert isinstance(ann, Annotation)


def _write_feature(tmp_path, content: str):
    """Helper to write a .feature file in tmp_path."""
    path = tmp_path / "test.feature"
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_annotations_feature_scope(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\nFeature: Login\n")
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "feature"
    assert anns[0].scope_name == "Login"
    assert anns[0].key == "jira"
    assert anns[0].value == "TICKET-1"


def test_extract_annotations_multiple_feature_level(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\n# @owner team-a\nFeature: Login\n")
    anns = extract_annotations(path)
    assert len(anns) == 2
    for ann in anns:
        assert ann.scope == "feature"
        assert ann.scope_name == "Login"


def test_extract_annotations_scenario_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path, "Feature: Login\n# @jira TICKET-2\nScenario: Successful login\n"
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "scenario"
    assert anns[0].scope_name == "Successful login"


def test_extract_annotations_step_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Login\nScenario: Successful login\n# @id STEP-001\n"
        "Given the user is on the login page\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "step"
    assert anns[0].scope_name == "Given the user is on the login page"


def test_extract_annotations_background_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Login\n# @setup db-init\nBackground:\n  Given a clean database\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "background"
    assert anns[0].scope_name == "Background"


def test_extract_annotations_rule_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Login\n# @rule-id R-001\nRule: Password must be strong\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "rule"
    assert anns[0].scope_name == "Password must be strong"


def test_extract_annotations_scope_changes(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a feature-level\n"
        "Feature: Test\n"
        "# @b scenario-level\n"
        "Scenario: S1\n"
        "# @c step-level\n"
        "Given x\n"
        "# @d scenario-level-2\n"
        "Scenario: S2\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 4
    assert anns[0].key == "a"
    assert anns[0].scope == "feature"
    assert anns[0].scope_name == "Test"
    assert anns[1].key == "b"
    assert anns[1].scope == "scenario"
    assert anns[1].scope_name == "S1"
    assert anns[2].key == "c"
    assert anns[2].scope == "step"
    assert anns[2].scope_name == "Given x"
    assert anns[3].key == "d"
    assert anns[3].scope == "scenario"
    assert anns[3].scope_name == "S2"


def test_extract_annotations_regular_comment_between(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a value1\n# This is a regular comment\n# @b value2\nFeature: Test\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 2
    for ann in anns:
        assert ann.scope == "feature"
        assert ann.scope_name == "Test"


def test_extract_annotations_empty_lines_between(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a value1\n\n# @b value2\nFeature: Test\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 2
    for ann in anns:
        assert ann.scope == "feature"


def test_extract_annotations_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        extract_annotations("nonexistent.feature")


def test_extract_annotations_unicode(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @key value\nFeature: Café — naïve\n")
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope_name == "Café — naïve"


def test_extract_annotations_scenario_outline(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n# @outline-id OL-1\nScenario Outline: Login with <user>\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "scenario"
    assert anns[0].scope_name == "Login with <user>"


def test_extract_annotations_examples_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\nScenario Outline: SO\n# @ex-id EX-1\nExamples:\n  | user |\n  | a |\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "examples"
    assert anns[0].scope_name == "Examples"


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("jira", "TICKET-42", "@jira-TICKET-42"),
        ("priority", "high", "@priority-high"),
        ("owner", "team-alpha", "@owner-team-alpha"),
    ],
)
def test_annotations_to_tags_basic(key: str, value: str, expected: str) -> None:
    ann = Annotation(key=key, value=value, line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == [expected]


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("smoke", "@smoke"),
        ("wip", "@wip"),
    ],
)
def test_annotations_to_tags_empty_value(key: str, expected: str) -> None:
    ann = Annotation(key=key, value="", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == [expected]


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("desc", "hello world", "@desc-hello-world"),
        ("ref", "REQ:001", "@ref-REQ-001"),
        ("path", "a/b/c", "@path-a-b-c"),
        ("complex", "a b:c/d", "@complex-a-b-c-d"),
    ],
)
def test_annotations_to_tags_sanitization(key: str, value: str, expected: str) -> None:
    ann = Annotation(key=key, value=value, line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == [expected]


def test_annotations_to_tags_empty_list() -> None:
    assert annotations_to_tags([]) == []


def test_annotations_to_tags_multiple() -> None:
    anns = [
        Annotation(key="a", value="1", line=1, scope="", scope_name=""),
        Annotation(key="b", value="2", line=2, scope="", scope_name=""),
        Annotation(key="c", value="3", line=3, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns) == ["@a-1", "@b-2", "@c-3"]


def test_annotations_to_tags_duplicates() -> None:
    anns = [
        Annotation(key="jira", value="TICKET-42", line=1, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-42", line=2, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns) == ["@jira-TICKET-42", "@jira-TICKET-42"]


def test_inject_metadata_basic(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\nFeature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert "feature" in context.metadata
    assert len(context.metadata["feature"]) == 1
    entry = context.metadata["feature"][0]
    assert entry["key"] == "jira"
    assert entry["value"] == "TICKET-1"
    assert entry["line"] == "1"
    assert entry["scope_name"] == "Test"


def test_inject_metadata_multiple_scopes(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a feature-val\n"
        "Feature: Test\n"
        "# @b scenario-val\n"
        "Scenario: S1\n"
        "# @c step-val\n"
        "Given x\n",
    )
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert len(context.metadata["feature"]) == 1
    assert len(context.metadata["scenario"]) == 1
    assert len(context.metadata["step"]) == 1


def test_inject_metadata_custom_prefix(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\nFeature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature, prefix="annotations")
    assert hasattr(context, "annotations")
    assert "feature" in context.annotations
    with pytest.raises(AttributeError):
        _ = context.metadata


def test_inject_metadata_no_filename() -> None:
    context = FakeContext()
    feature = FakeFeature(filename=None)
    inject_metadata(context, feature)
    with pytest.raises(AttributeError):
        _ = context.metadata


def test_inject_metadata_no_annotations(tmp_path) -> None:
    path = _write_feature(tmp_path, "Feature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert context.metadata == {}


def test_inject_metadata_multiple_same_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a val1\n# @b val2\nFeature: Test\n",
    )
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert len(context.metadata["feature"]) == 2


def test_inject_metadata_entry_structure(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\nFeature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    entry = context.metadata["feature"][0]
    assert set(entry.keys()) == {"key", "value", "line", "scope_name"}


def test_inject_metadata_line_is_string(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\nFeature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    entry = context.metadata["feature"][0]
    assert isinstance(entry["line"], str)
