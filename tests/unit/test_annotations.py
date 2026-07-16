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
        "# @before-feature: Given the database is clean",
        "# @after-scenario: Then the cache is cleared",
        "# @before-all: Given global setup",
        "# @after-all: Then global teardown",
        "# @before-step: Given step setup",
        "# @after-step: Then step teardown",
        "# @before-scenario: Given scenario setup",
        "# @after-feature: Then feature teardown",
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


def test_annotations_to_tags_dedup_removes_duplicates() -> None:
    anns = [
        Annotation(key="jira", value="TICKET-42", line=1, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-42", line=2, scope="", scope_name=""),
        Annotation(key="owner", value="team-a", line=3, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-42", line=4, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns, dedup=True) == [
        "@jira-TICKET-42",
        "@owner-team-a",
    ]


def test_annotations_to_tags_dedup_preserves_order() -> None:
    anns = [
        Annotation(key="b", value="2", line=1, scope="", scope_name=""),
        Annotation(key="a", value="1", line=2, scope="", scope_name=""),
        Annotation(key="b", value="2", line=3, scope="", scope_name=""),
        Annotation(key="c", value="3", line=4, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns, dedup=True) == ["@b-2", "@a-1", "@c-3"]


def test_annotations_to_tags_dedup_empty_value() -> None:
    anns = [
        Annotation(key="smoke", value="", line=1, scope="", scope_name=""),
        Annotation(key="smoke", value="", line=2, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns, dedup=True) == ["@smoke"]


def test_annotations_to_tags_key_sanitized() -> None:
    ann = Annotation(key="my_key", value="val", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@my-key-val"]


def test_annotations_to_tags_key_with_dot_sanitized() -> None:
    ann = Annotation(key="config.sub", value="true", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@config-sub-true"]


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


# ---------------------------------------------------------------------------
# Edge cases: annotations at end of file without scope keyword
# ---------------------------------------------------------------------------


def test_extract_annotations_pending_at_end_of_file(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @jira TICKET-1\n# @owner team-a\n")
    anns = extract_annotations(path)
    assert len(anns) == 2
    assert anns[0].key == "jira"
    assert anns[0].value == "TICKET-1"
    assert anns[0].scope == "feature"
    assert anns[0].scope_name == ""
    assert anns[1].key == "owner"
    assert anns[1].value == "team-a"


def test_extract_annotations_pending_after_feature_no_scenario(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n# @jira TICKET-2\n# @owner team-b\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 2
    for ann in anns:
        assert ann.scope == "feature"
        assert ann.scope_name == "Test"


def test_extract_annotations_only_regular_comments(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# This is a comment\n# Another comment\nFeature: Test\n",
    )
    anns = extract_annotations(path)
    assert anns == []


def test_extract_annotations_empty_file(tmp_path) -> None:
    path = _write_feature(tmp_path, "")
    anns = extract_annotations(path)
    assert anns == []


def test_extract_annotations_only_feature_keyword(tmp_path) -> None:
    path = _write_feature(tmp_path, "Feature: Test\n")
    anns = extract_annotations(path)
    assert anns == []


def test_extract_annotations_multiple_annotations_same_line_scope(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\nScenario: S1\n# @a 1\n# @b 2\n# @c 3\nGiven a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 3
    for ann in anns:
        assert ann.scope == "step"
        assert ann.scope_name == "Given a step"


def test_extract_annotations_annotation_with_special_chars_in_value(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @url https://example.com/path?q=1&r=2\nFeature: Test\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "url"
    assert anns[0].value == "https://example.com/path?q=1&r=2"


def test_extract_annotations_key_with_dots_not_matched(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @config.value true\nFeature: Test\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "config"
    assert anns[0].value == "value true"


def test_inject_metadata_no_annotations_empty_file(tmp_path) -> None:
    path = _write_feature(tmp_path, "")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert context.metadata == {}


# ---------------------------------------------------------------------------
# Bug fix tests: lifecycle hook exclusion, tag sanitization
# ---------------------------------------------------------------------------


def test_extract_annotations_excludes_lifecycle_hooks(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @jira TICKET-1\n"
        "# @before-feature: Given the database is clean\n"
        "# @after-scenario: Then the cache is cleared\n"
        "Feature: Test\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "jira"
    assert anns[0].value == "TICKET-1"


def test_extract_annotations_lifecycle_hooks_not_in_metadata(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-all: Given global setup\n"
        "# @jira TICKET-1\n"
        "# @after-all: Then global teardown\n"
        "Feature: Test\n",
    )
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    inject_metadata(context, feature)
    assert len(context.metadata["feature"]) == 1
    assert context.metadata["feature"][0]["key"] == "jira"


def test_annotations_to_tags_special_chars_sanitized() -> None:
    ann = Annotation(key="x", value="a@b!c&d", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-a-b-c-d"]


def test_annotations_to_tags_parentheses_sanitized() -> None:
    ann = Annotation(key="x", value="hello(world)", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-hello-world"]


def test_annotations_to_tags_multiple_special_chars() -> None:
    ann = Annotation(key="x", value="a@b!c&d,e", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-a-b-c-d-e"]


def test_annotations_to_tags_hyphen_preserved() -> None:
    ann = Annotation(key="x", value="already-hyphenated", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-already-hyphenated"]


def test_annotations_to_tags_underscore_sanitized() -> None:
    ann = Annotation(key="x", value="under_score", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-under-score"]


def test_annotations_to_tags_whitespace_only_value() -> None:
    ann = Annotation(key="x", value="   ", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x"]


def test_annotations_to_tags_value_only_special_chars() -> None:
    ann = Annotation(key="x", value="@@@!!!", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x"]


# ---------------------------------------------------------------------------
# Bug fix tests: := separator, key-only annotations
# ---------------------------------------------------------------------------


def test_parse_annotation_line_colon_equals_separator() -> None:
    ann = parse_annotation_line("# @key:=value", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == "value"


def test_parse_annotation_line_colon_equals_with_spaces() -> None:
    ann = parse_annotation_line("# @key:= value", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == "value"


def test_parse_annotation_line_key_only_no_value() -> None:
    ann = parse_annotation_line("# @key", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == ""


# ---------------------------------------------------------------------------
# Bug fix tests: case-insensitive lifecycle exclusion, double hyphens, BOM
# ---------------------------------------------------------------------------


def test_parse_annotation_line_excludes_uppercase_lifecycle_hook() -> None:
    assert parse_annotation_line("# @BEFORE-FEATURE: Given step", 1) is None
    assert parse_annotation_line("# @After-Scenario: Then step", 1) is None
    assert parse_annotation_line("# @before-ALL: Given step", 1) is None


def test_annotations_to_tags_collapses_double_hyphens() -> None:
    ann = Annotation(key="x", value="--double--dash--", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-double-dash"]


def test_annotations_to_tags_collapses_hyphens_from_special_chars() -> None:
    ann = Annotation(key="x", value="a@@b!!c", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@x-a-b-c"]


def test_extract_annotations_bom_file(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @priority high\nFeature: Test\n",
    )
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "priority"
    assert anns[0].value == "high"


def test_extract_annotations_star_keyword_as_step(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n  Scenario: S\n    # @step-level value\n    * I do something\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "step"
    assert anns[0].scope_name == "* I do something"


def test_annotations_to_tags_key_only_hyphens_skipped() -> None:
    ann = Annotation(key="---", value="val", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == []


def test_annotations_to_tags_key_only_hyphens_no_value_skipped() -> None:
    ann = Annotation(key="---", value="", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == []


def test_annotations_to_tags_mixed_valid_and_empty_key() -> None:
    anns = [
        Annotation(key="---", value="skip", line=1, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-1", line=2, scope="", scope_name=""),
        Annotation(key="---", value="skip2", line=3, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns) == ["@jira-TICKET-1"]


def test_annotations_to_tags_key_underscore_sanitized() -> None:
    ann = Annotation(key="test_case", value="high", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@test-case-high"]


def test_annotations_to_tags_key_mixed_special_sanitized() -> None:
    ann = Annotation(key="a@b#c", value="x", line=1, scope="", scope_name="")
    assert annotations_to_tags([ann]) == ["@a-b-c-x"]


def test_annotations_to_tags_dedup_with_empty_key_skipped() -> None:
    anns = [
        Annotation(key="---", value="skip", line=1, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-1", line=2, scope="", scope_name=""),
        Annotation(key="jira", value="TICKET-1", line=3, scope="", scope_name=""),
    ]
    assert annotations_to_tags(anns, dedup=True) == ["@jira-TICKET-1"]


def test_extract_annotations_feature_no_name(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @jira TICKET-1\nFeature:\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "feature"
    assert anns[0].scope_name == ""


def test_extract_annotations_tabs_as_indentation(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n"
        "\tScenario: S\n"
        "\t\tGiven a step\n"
        "# @step-level value\n"
        "\t\tWhen I do something\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "step"


def test_extract_annotations_tag_line_ignored(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "@smoke @wip\nFeature: Test\n  Scenario: S\n    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 0


def test_parse_annotation_line_key_with_digits() -> None:
    ann = parse_annotation_line("# @123 value", 1)
    assert ann is not None
    assert ann.key == "123"
    assert ann.value == "value"


def test_parse_annotation_line_key_starts_with_hyphen() -> None:
    ann = parse_annotation_line("# @-key value", 1)
    assert ann is not None
    assert ann.key == "-key"
    assert ann.value == "value"


def test_parse_annotation_line_double_colon_separator() -> None:
    ann = parse_annotation_line("# @key:: value", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == "value"


def test_parse_annotation_line_double_equals_separator() -> None:
    ann = parse_annotation_line("# @key== value", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == "value"


def test_parse_annotation_line_triple_separator() -> None:
    ann = parse_annotation_line("# @key:=: value", 1)
    assert ann is not None
    assert ann.key == "key"
    assert ann.value == ": value"


def test_parse_annotation_line_value_with_separators() -> None:
    ann = parse_annotation_line("# @url http://example.com:8080/path", 1)
    assert ann is not None
    assert ann.key == "url"
    assert ann.value == "http://example.com:8080/path"


def test_parse_annotation_line_value_with_equals() -> None:
    ann = parse_annotation_line("# @expr a=b+c=d", 1)
    assert ann is not None
    assert ann.key == "expr"
    assert ann.value == "a=b+c=d"


def test_inject_metadata_empty_string_filename() -> None:
    context = FakeContext()
    feature = FakeFeature(filename="")
    inject_metadata(context, feature)
    assert not hasattr(context, "metadata")


def test_annotations_to_tags_unicode_value() -> None:
    ann = Annotation(key="name", value="café", line=1, scope="feature", scope_name="F")
    tags = annotations_to_tags([ann])
    assert tags == ["@name-caf"]


def test_annotations_to_tags_value_only_whitespace() -> None:
    ann = Annotation(key="key", value="   ", line=1, scope="feature", scope_name="F")
    tags = annotations_to_tags([ann])
    assert tags == ["@key"]


def test_parse_annotation_line_at_sign_only() -> None:
    with pytest.raises(AnnotationParseError):
        parse_annotation_line("# @", 1)


def test_parse_annotation_line_at_sign_space() -> None:
    with pytest.raises(AnnotationParseError):
        parse_annotation_line("# @ ", 1)


def test_extract_annotations_pending_at_end(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n  Scenario: S1\n    Given a step\n# @trailing TRAIL-1\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "trailing"
    assert anns[0].value == "TRAIL-1"
    assert anns[0].scope == "step"


def test_extract_annotations_rule_then_scenario(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n"
        "# @rule-ann R-1\n"
        "Rule: My Rule\n"
        "# @scenario-ann S-1\n"
        "Scenario: Inside Rule\n"
        "    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 2
    assert anns[0].key == "rule-ann"
    assert anns[0].scope == "rule"
    assert anns[1].key == "scenario-ann"
    assert anns[1].scope == "scenario"


def test_extract_annotations_crlf_line_endings(tmp_path) -> None:
    content = "# @jira TICKET-1\r\nFeature: Test\r\n  Scenario: S1\r\n    Given a step\r\n"
    path = tmp_path / "test.feature"
    path.write_bytes(content.encode("utf-8"))
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "jira"
    assert anns[0].value == "TICKET-1"
    assert anns[0].scope == "feature"


def test_extract_annotations_multiple_features(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @a A-1\n"
        "Feature: First\n"
        "  Scenario: S1\n"
        "    Given a step\n"
        "# @b B-1\n"
        "Feature: Second\n"
        "  Scenario: S2\n"
        "    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 2
    assert anns[0].key == "a"
    assert anns[0].scope_name == "First"
    assert anns[1].key == "b"
    assert anns[1].scope_name == "Second"


def test_annotations_to_tags_key_with_underscore() -> None:
    ann = Annotation(key="my_key", value="val", line=1, scope="feature", scope_name="F")
    tags = annotations_to_tags([ann])
    assert tags == ["@my-key-val"]


def test_annotations_to_tags_key_with_dot() -> None:
    ann = Annotation(key="config.key", value="val", line=1, scope="feature", scope_name="F")
    tags = annotations_to_tags([ann])
    assert tags == ["@config-key-val"]


def test_extract_annotations_scenario_template(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n# @template-id T-1\nScenario Template: Login with <user>\n  Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "template-id"
    assert anns[0].value == "T-1"
    assert anns[0].scope == "scenario"
    assert anns[0].scope_name == "Login with <user>"


def test_annotations_to_tags_empty_list_dedup() -> None:
    assert annotations_to_tags([], dedup=True) == []


def test_extract_annotations_between_background_and_scenario(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n"
        "Background:\n"
        "  Given a step\n"
        "# @bg-ann BG-1\n"
        "Scenario: S1\n"
        "  Given another step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "bg-ann"
    assert anns[0].scope == "scenario"
    assert anns[0].scope_name == "S1"


def test_parse_annotation_line_just_hash() -> None:
    ann = parse_annotation_line("#", 1)
    assert ann is None


def test_parse_annotation_line_hash_with_text() -> None:
    ann = parse_annotation_line("# just a comment", 1)
    assert ann is None


def test_extract_annotations_feature_with_tags(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "@smoke @regression\n"
        "# @jira TICKET-1\n"
        "Feature: Tagged Feature\n"
        "  Scenario: S1\n"
        "    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].key == "jira"
    assert anns[0].scope == "feature"


def test_extract_annotations_feature_no_space_after_colon(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @jira TICKET-1\nFeature:NoSpace\n  Scenario: S1\n    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "feature"
    assert anns[0].scope_name == "NoSpace"


def test_extract_annotations_scenario_no_space_after_colon(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n# @id SC-001\nScenario:NoSpace\n  Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "scenario"
    assert anns[0].scope_name == "NoSpace"


def test_extract_annotations_rule_no_space_after_colon(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n# @rule-ann R-1\nRule:NoSpace\n  Scenario: S1\n    Given a step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "rule"
    assert anns[0].scope_name == "NoSpace"


def test_extract_annotations_background_no_space_after_colon(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n"
        "# @bg BG-1\n"
        "Background:NoSpace\n"
        "  Given a step\n"
        "Scenario: S1\n"
        "  Given another step\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "background"
    assert anns[0].scope_name == "Background"


def test_extract_annotations_examples_no_space_after_colon(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "Feature: Test\n"
        "Scenario Outline: S1\n"
        "  Given a step\n"
        "# @ex EX-1\n"
        "Examples:NoSpace\n"
        "  | key |\n"
        "  | val |\n",
    )
    anns = extract_annotations(path)
    assert len(anns) == 1
    assert anns[0].scope == "examples"
    assert anns[0].scope_name == "Examples"
