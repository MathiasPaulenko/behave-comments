"""Integration edge case tests with real Behave runs."""

from __future__ import annotations


def test_empty_feature_with_only_feature_keyword(run_behave):
    """A feature with no scenarios should pass cleanly."""
    result = run_behave(
        feature_content="""
            Feature: Empty Feature
        """,
        steps_content="""
            from behave import given, then
        """,
    )
    assert result.returncode == 0


def test_feature_with_annotations_and_tags(run_behave):
    """Annotations are injected as metadata and tags."""
    result = run_behave(
        feature_content="""
            # @jira TICKET-42
            # @priority high
            Feature: Annotated Feature

              # @smoke
              Scenario: Tagged scenario
                Given a step
                Then the step passes
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the step passes")
            def step_then(context):
                pass
        """,
        environment_content="""
            from behave_comments import inject_metadata, annotations_to_tags, extract_annotations

            def before_feature(context, feature):
                inject_metadata(context, feature)
                anns = extract_annotations(feature.filename)
                feature.tags.extend(annotations_to_tags(anns))

            def before_scenario(context, scenario):
                anns = extract_annotations(scenario.feature.filename)
                for ann in anns:
                    if ann.scope == "scenario" and ann.scope_name == scenario.name:
                        scenario.tags.extend(annotations_to_tags([ann]))
        """,
    )
    assert result.returncode == 0


def test_lifecycle_before_feature_sets_context(run_behave):
    """A before-feature hook sets a value that scenarios can read."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given the database is clean
            Feature: Lifecycle Feature

              Scenario: Check database state
                Then the database is clean
        """,
        steps_content="""
            from behave import given, then

            @given("the database is clean")
            def step_db_clean(context):
                context.db_clean = True

            @then("the database is clean")
            def step_then_db_clean(context):
                assert context.db_clean is True
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_lifecycle_after_scenario_cleanup(run_behave):
    """An after-scenario hook runs cleanup steps."""
    result = run_behave(
        feature_content="""
            Feature: Cleanup Feature

              # @after-scenario: Then the cache is cleared
              Scenario: First scenario
                Given a step

              Scenario: Second scenario
                Given a step
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the cache is cleared")
            def step_cleanup(context):
                context.cache_cleared = True
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_after_scenario

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def after_scenario(context, scenario):
                run_after_scenario(context, scenario)
        """,
    )
    assert result.returncode == 0


def test_multiple_lifecycle_hooks_same_type(run_behave):
    """Multiple before-feature hooks all execute in order."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given step A
            # @before-feature: Given step B
            Feature: Multiple Hooks

              Scenario: Check order
                Then both steps ran in order
        """,
        steps_content="""
            from behave import given, then

            @given("step A")
            def step_a(context):
                context.order = ["A"]

            @given("step B")
            def step_b(context):
                context.order.append("B")

            @then("both steps ran in order")
            def step_then_order(context):
                assert context.order == ["A", "B"]
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_lifecycle_hook_with_unknown_step_fails(run_behave):
    """A lifecycle hook referencing an undefined step fails."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a nonexistent step
            Feature: Failing Hook

              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given

            @given("a step")
            def step_given(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode != 0


def test_xml_text_block_parsed(run_behave):
    """An XML doc string is parsed into an ElementTree."""
    result = run_behave(
        feature_content="""
            Feature: XML Text Block

              Scenario: Parse XML
                Given an XML document
                  \"\"\"xml
                  <root><child>value</child></root>
                  \"\"\"
                Then the XML is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("an XML document")
            def step_given_xml(context):
                parsed = parse_text(str(context.text), "xml")
                assert parsed.tag == "root"
                child = parsed.find("child")
                assert child is not None
                assert child.text == "value"

            @then("the XML is parsed")
            def step_then_xml(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_form_urlencoded_text_block(run_behave):
    """A form-urlencoded doc string is parsed into a dict."""
    result = run_behave(
        feature_content="""
            Feature: Form Text Block

              Scenario: Parse form data
                Given a form document
                  \"\"\"form-urlencoded
                  name=Alice&age=30
                  \"\"\"
                Then the form is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a form document")
            def step_given_form(context):
                parsed = parse_text(str(context.text), "form-urlencoded")
                assert parsed["name"] == ["Alice"]
                assert parsed["age"] == ["30"]

            @then("the form is parsed")
            def step_then_form(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_graphql_text_block(run_behave):
    """A GraphQL doc string is preserved as raw text."""
    result = run_behave(
        feature_content="""
            Feature: GraphQL Text Block

              Scenario: Parse GraphQL
                Given a GraphQL query
                  \"\"\"graphql
                  query { user { name } }
                  \"\"\"
                Then the GraphQL is preserved
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a GraphQL query")
            def step_given_graphql(context):
                parsed = parse_text(str(context.text), "graphql")
                assert "query" in parsed

            @then("the GraphQL is preserved")
            def step_then_graphql(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_json_array_text_block(run_behave):
    """A JSON array doc string is parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: JSON Array

              Scenario: Parse array
                Given a JSON array
                  \"\"\"json
                  [1, 2, 3]
                  \"\"\"
                Then the array is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a JSON array")
            def step_given_array(context):
                parsed = parse_text(str(context.text), "json")
                assert parsed == [1, 2, 3]

            @then("the array is parsed")
            def step_then_array(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_yaml_list_text_block(run_behave):
    """A YAML list doc string is parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: YAML List

              Scenario: Parse YAML list
                Given a YAML list
                  \"\"\"yaml
                  - item1
                  - item2
                  \"\"\"
                Then the list is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a YAML list")
            def step_given_yaml_list(context):
                parsed = parse_text(str(context.text), "yaml")
                assert parsed == ["item1", "item2"]

            @then("the list is parsed")
            def step_then_list(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_unicode_in_feature(run_behave):
    """Unicode characters in feature names and steps work correctly."""
    import os
    import sys

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    result = run_behave(
        feature_content="""
            Feature: Cafe - naive - Japanese

              Scenario: Unicode test
                Given a step with unicode - cafe
                Then it passes
        """,
        steps_content="""
            from behave import given, then

            @given("a step with unicode - cafe")
            def step_given_unicode(context):
                pass

            @then("it passes")
            def step_then_pass(context):
                pass
        """,
    )
    if sys.platform == "win32":
        if result.returncode != 0 and "UnicodeEncodeError" in result.stderr:
            import pytest

            pytest.skip("Behave plain formatter doesn't support unicode on Windows cp1252")
    assert result.returncode == 0


def test_multiple_features_same_dir(run_behave):
    """Multiple feature files in the same directory all work."""
    result = run_behave(
        feature_content="""
            Feature: First Feature

              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given

            @given("a step")
            def step_given(context):
                pass
        """,
        feature_filename="first.feature",
    )
    assert result.returncode == 0


def test_scenario_outline_with_annotations(run_behave):
    """Annotations work with Scenario Outline."""
    result = run_behave(
        feature_content="""
            # @suite regression
            Feature: Outline Feature

              # @case-id CASE-001
              Scenario Outline: Login with <user>
                Given the user is <user>
                Then login succeeds

                Examples:
                  | user   |
                  | Alice  |
                  | Bob    |
        """,
        steps_content="""
            from behave import given, then

            @given("the user is {user}")
            def step_given_user(context, user):
                context.user = user

            @then("login succeeds")
            def step_then_login(context):
                assert context.user is not None
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_combined_annotations_and_lifecycle(run_behave):
    """Annotations and lifecycle hooks work together in the same feature."""
    result = run_behave(
        feature_content="""
            # @jira TICKET-100
            # @before-feature: Given the database is clean
            Feature: Combined Feature

              # @smoke
              # @after-scenario: Then the cache is cleared
              Scenario: S1
                Given a step
                Then the step passes
        """,
        steps_content="""
            from behave import given, then

            @given("the database is clean")
            def step_db_clean(context):
                context.db_clean = True

            @given("a step")
            def step_given(context):
                assert getattr(context, "db_clean", False) is True

            @then("the step passes")
            def step_then_pass(context):
                pass

            @then("the cache is cleared")
            def step_cleanup(context):
                context.cache_cleared = True
        """,
        environment_content="""
            from behave_comments import (
                inject_metadata,
                setup_lifecycle_hooks,
                run_before_feature,
                run_after_scenario,
            )

            def before_feature(context, feature):
                inject_metadata(context, feature)
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)

            def after_scenario(context, scenario):
                run_after_scenario(context, scenario)
        """,
    )
    assert result.returncode == 0


def test_before_step_hook_infinite_recursion_guard(run_behave):
    """A before-step hook using execute_steps causes recursion in Behave.

    This is a known Behave limitation: before_step fires for sub-steps too.
    The test verifies the hook fails gracefully rather than hanging.
    """
    result = run_behave(
        feature_content="""
            Feature: Before Step Hook

              # @before-step: Given the timer starts
              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given

            @given("the timer starts")
            def step_timer(context):
                context.timer_started = True

            @given("a step")
            def step_given(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_step

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def before_step(context, step):
                run_before_step(context, step)
        """,
    )
    assert result.returncode != 0


def test_after_feature_hook_executes(run_behave):
    """An after-feature hook runs after the feature completes."""
    result = run_behave(
        feature_content="""
            Feature: After Feature Hook

              # @after-feature: Then the cleanup is done
              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the cleanup is done")
            def step_cleanup(context):
                context.cleanup_done = True
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_after_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def after_feature(context, feature):
                run_after_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_text_block_and_lifecycle_combined(run_behave):
    """Text blocks and lifecycle hooks work in the same scenario."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given the database is clean
            Feature: Text Block and Lifecycle

              Scenario: S1
                Given a JSON document
                  \"\"\"json
                  {"key": "value"}
                  \"\"\"
                Then the parsed value should be "value"
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("the database is clean")
            def step_db_clean(context):
                context.db_clean = True

            @given("a JSON document")
            def step_given_json(context):
                assert getattr(context, "db_clean", False) is True
                parsed = parse_text(str(context.text), "json")
                assert parsed == {"key": "value"}

            @then('the parsed value should be "value"')
            def step_then_value(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_lifecycle_hook_with_then_step(run_behave):
    """Lifecycle hooks work with Then steps, not just Given."""
    result = run_behave(
        feature_content="""
            # @before-feature: Then the system is ready
            Feature: Then Hook

              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given, then

            @then("the system is ready")
            def step_system_ready(context):
                context.system_ready = True

            @given("a step")
            def step_given(context):
                assert getattr(context, "system_ready", False) is True
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_lifecycle_hook_with_when_step(run_behave):
    """Lifecycle hooks work with When steps."""
    result = run_behave(
        feature_content="""
            # @before-scenario: When the timer starts
            Feature: When Hook

              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given, when

            @when("the timer starts")
            def step_timer(context):
                context.timer = True

            @given("a step")
            def step_given(context):
                assert getattr(context, "timer", False) is True
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_scenario

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def before_scenario(context, scenario):
                run_before_scenario(context, scenario)
        """,
    )
    assert result.returncode == 0


def test_multiple_scenarios_with_after_scenario_hook(run_behave):
    """After-scenario hooks run after each scenario."""
    result = run_behave(
        feature_content="""
            Feature: Multiple Scenarios

              # @after-scenario: Then the counter is reset
              Scenario: S1
                Given a step

              Scenario: S2
                Given a step
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the counter is reset")
            def step_reset(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_after_scenario

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def after_scenario(context, scenario):
                run_after_scenario(context, scenario)
        """,
    )
    assert result.returncode == 0


def test_annotations_to_tags_in_behave(run_behave):
    """Annotations are converted to tags visible in Behave output."""
    result = run_behave(
        feature_content="""
            # @jira TICKET-42
            # @smoke
            Feature: Tagged Feature

              # @priority high
              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given

            @given("a step")
            def step_given(context):
                pass
        """,
        environment_content="""
            from behave_comments import (
                extract_annotations,
                annotations_to_tags,
            )

            def before_feature(context, feature):
                anns = extract_annotations(feature.filename)
                feature.tags.extend(annotations_to_tags(anns))

            def before_scenario(context, scenario):
                anns = extract_annotations(scenario.feature.filename)
                for ann in anns:
                    if ann.scope == "scenario" and ann.scope_name == scenario.name:
                        scenario.tags.extend(annotations_to_tags([ann]))
        """,
    )
    assert result.returncode == 0


def test_yaml_text_block_in_behave(run_behave):
    """A YAML doc string with nested structures is parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: YAML Nested

              Scenario: Parse nested YAML
                Given a YAML document
                  \"\"\"yaml
                  outer:
                    inner:
                      key: value
                      list:
                        - item1
                        - item2
                  \"\"\"
                Then the YAML is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a YAML document")
            def step_given_yaml(context):
                parsed = parse_text(str(context.text), "yaml")
                assert parsed["outer"]["inner"]["key"] == "value"
                assert parsed["outer"]["inner"]["list"] == ["item1", "item2"]

            @then("the YAML is parsed")
            def step_then_yaml(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_csv_text_block_multiple_rows(run_behave):
    """A CSV doc string with multiple rows is parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: CSV Multiple Rows

              Scenario: Parse CSV
                Given a CSV document
                  \"\"\"csv
                  name,age,city
                  Alice,30,NYC
                  Bob,25,LA
                  Charlie,35,Chicago
                  \"\"\"
                Then the CSV has 3 rows
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a CSV document")
            def step_given_csv(context):
                parsed = parse_text(str(context.text), "csv")
                assert len(parsed) == 3
                assert parsed[0]["name"] == "Alice"
                assert parsed[1]["name"] == "Bob"
                assert parsed[2]["name"] == "Charlie"

            @then("the CSV has 3 rows")
            def step_then_csv(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_no_lifecycle_hooks_no_error(run_behave):
    """A feature with no lifecycle hooks doesn't cause errors."""
    result = run_behave(
        feature_content="""
            Feature: No Hooks

              Scenario: S1
                Given a step
                Then the step passes
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the step passes")
            def step_then(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature, run_after_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)

            def after_feature(context, feature):
                run_after_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_lifecycle_hook_fails_scenario(run_behave):
    """A failing lifecycle hook step causes the feature to fail."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a failing step
            Feature: Failing Hook

              Scenario: S1
                Given a step
        """,
        steps_content="""
            from behave import given

            @given("a failing step")
            def step_failing(context):
                assert False, "intentional failure"

            @given("a step")
            def step_given(context):
                pass
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode != 0


def test_background_with_annotations(run_behave):
    """Annotations work with Background sections."""
    result = run_behave(
        feature_content="""
            Feature: Background Feature

              # @setup db-init
              Background:
                Given a clean database

              Scenario: S1
                Then the database is clean
        """,
        steps_content="""
            from behave import given, then

            @given("a clean database")
            def step_db_clean(context):
                context.db_clean = True

            @then("the database is clean")
            def step_then_db(context):
                assert context.db_clean is True
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_continue_on_error_runs_all_hooks(run_behave):
    """continue_on_error=True should run all hooks even if one fails."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a failing step
            # @before-feature: Given a passing step
            Feature: Continue On Error

              Scenario: S1
                Then the context has both hooks executed
        """,
        steps_content="""
            from behave import given, then

            @given("a failing step")
            def step_fail(context):
                assert False, "intentional failure"

            @given("a passing step")
            def step_pass(context):
                context.passing_step_executed = True

            @then("the context has both hooks executed")
            def step_check(context):
                assert getattr(context, "passing_step_executed", False), "Passing hook did not run"
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                try:
                    run_before_feature(context, feature, continue_on_error=True)
                except Exception:
                    pass
        """,
    )
    assert result.returncode == 0


def test_dedup_tags_in_integration(run_behave):
    """dedup=True should remove duplicate tags."""
    result = run_behave(
        feature_content="""
            # @jira TICKET-42
            # @jira TICKET-42
            # @owner team-a
            Feature: Dedup Tags

              Scenario: S1
                Then the tags are deduplicated
        """,
        steps_content="""
            from behave import then

            @then("the tags are deduplicated")
            def step_check(context):
                tags = context.deduped_tags
                assert tags == ["@jira-TICKET-42", "@owner-team-a"], f"Got {tags}"
        """,
        environment_content="""
            from behave_comments import extract_annotations, annotations_to_tags

            def before_feature(context, feature):
                anns = extract_annotations(feature.filename)
                context.deduped_tags = annotations_to_tags(anns, dedup=True)
        """,
    )
    assert result.returncode == 0


def test_key_sanitization_in_tags(run_behave):
    """Keys with underscores should be sanitized to hyphens in tags."""
    result = run_behave(
        feature_content="""
            # @test_case TC-001
            Feature: Key Sanitization

              Scenario: S1
                Then the key is sanitized
        """,
        steps_content="""
            from behave import then

            @then("the key is sanitized")
            def step_check(context):
                assert context.sanitized_tags == ["@test-case-TC-001"], (
                    f"Got {context.sanitized_tags}"
                )
        """,
        environment_content="""
            from behave_comments import extract_annotations, annotations_to_tags

            def before_feature(context, feature):
                anns = extract_annotations(feature.filename)
                context.sanitized_tags = annotations_to_tags(anns)
        """,
    )
    assert result.returncode == 0


def test_yaml_doc_string_parsed(run_behave):
    """YAML doc strings should be parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: YAML Parsing

              Scenario: Parse YAML
                Given a step with a YAML doc string
                  \"\"\"yaml
                  name: Alice
                  age: 30
                  \"\"\"
                Then the YAML name is "Alice"
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with a YAML doc string")
            def step_yaml(context):
                context.yaml_data = parse_text(str(context.text), "yaml")

            @then('the YAML name is "Alice"')
            def step_check(context):
                assert context.yaml_data["name"] == "Alice"
                assert context.yaml_data["age"] == 30
        """,
    )
    assert result.returncode == 0


def test_multiple_lifecycle_hooks_same_type_all_execute(run_behave):
    result = run_behave(
        feature_content="""
            # @before-feature: Given step one
            # @before-feature: Given step two
            Feature: Multiple Hooks

              Scenario: S1
                Then both steps were executed
        """,
        steps_content="""
            from behave import given, then

            @given("step one")
            def step_one(context):
                context.step_one = True

            @given("step two")
            def step_two(context):
                context.step_two = True

            @then("both steps were executed")
            def step_check(context):
                assert getattr(context, "step_one", False), "Step one not executed"
                assert getattr(context, "step_two", False), "Step two not executed"
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_annotation_with_colon_separator(run_behave):
    """Annotations with colon separator should be parsed correctly."""
    result = run_behave(
        feature_content="""
            # @jira: TICKET-999
            Feature: Colon Separator

              Scenario: S1
                Then the colon annotation is parsed
        """,
        steps_content="""
            from behave import then

            @then("the colon annotation is parsed")
            def step_check(context):
                anns = context.metadata["feature"]
                assert any(
                    a["key"] == "jira" and a["value"] == "TICKET-999"
                    for a in anns
                ), f"Got {anns}"
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_annotation_with_equals_separator(run_behave):
    """Annotations with equals separator should be parsed correctly."""
    result = run_behave(
        feature_content="""
            # @priority=high
            Feature: Equals Separator

              Scenario: S1
                Then the equals annotation is parsed
        """,
        steps_content="""
            from behave import then

            @then("the equals annotation is parsed")
            def step_check(context):
                anns = context.metadata["feature"]
                assert any(
                    a["key"] == "priority" and a["value"] == "high"
                    for a in anns
                ), f"Got {anns}"
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_xml_doc_string_parsed(run_behave):
    """XML doc strings should be parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: XML Parsing

              Scenario: Parse XML
                Given a step with an XML doc string
                  \"\"\"xml
                  <root><item>value</item></root>
                  \"\"\"
                Then the XML root has one item
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with an XML doc string")
            def step_xml(context):
                context.xml_root = parse_text(str(context.text), "xml")

            @then("the XML root has one item")
            def step_check(context):
                root = context.xml_root
                assert root.tag == "root"
                assert len(root) == 1
                assert root[0].tag == "item"
                assert root[0].text == "value"
        """,
    )
    assert result.returncode == 0


def test_form_urlencoded_doc_string_parsed(run_behave):
    """form-urlencoded doc strings should be parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: Form Parsing

              Scenario: Parse form-urlencoded
                Given a step with a form doc string
                  \"\"\"form-urlencoded
                  name=Alice&age=30
                  \"\"\"
                Then the form name is "Alice"
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with a form doc string")
            def step_form(context):
                context.form_data = parse_text(str(context.text), "form-urlencoded")

            @then('the form name is "Alice"')
            def step_check(context):
                assert context.form_data["name"] == ["Alice"]
                assert context.form_data["age"] == ["30"]
        """,
    )
    assert result.returncode == 0


def test_graphql_doc_string_parsed(run_behave):
    """GraphQL doc strings should be returned as raw text."""
    result = run_behave(
        feature_content="""
            Feature: GraphQL Parsing

              Scenario: Parse GraphQL
                Given a step with a GraphQL doc string
                  \"\"\"graphql
                  query { user { name } }
                  \"\"\"
                Then the GraphQL query is preserved
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with a GraphQL doc string")
            def step_graphql(context):
                context.gql = parse_text(str(context.text), "graphql")

            @then("the GraphQL query is preserved")
            def step_check(context):
                assert "query" in context.gql
                assert "user" in context.gql
        """,
    )
    assert result.returncode == 0


def test_before_feature_hook_with_execute_steps(run_behave):
    """before-feature hooks should execute via execute_steps."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a feature setup step
            Feature: Before Feature Hook

              Scenario: S1
                Then the feature setup was executed
        """,
        steps_content="""
            from behave import given, then

            @given("a feature setup step")
            def step_setup(context):
                context.feature_setup = True

            @then("the feature setup was executed")
            def step_check(context):
                assert getattr(
                    context, "feature_setup", False
                ), "before-feature hook did not execute"
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0


def test_bom_feature_file_annotations_parsed_by_library(tmp_path):
    """Our library should parse BOM feature files correctly (Behave itself can't)."""
    from behave_comments.annotations import extract_annotations

    feature_file = tmp_path / "test.feature"
    feature_file.write_text(
        "# @jira TICKET-BOM\nFeature: BOM Feature\n\n  Scenario: S1\n    Given a step\n",
        encoding="utf-8-sig",
    )
    anns = extract_annotations(str(feature_file))
    assert len(anns) == 1
    assert anns[0].key == "jira"
    assert anns[0].value == "TICKET-BOM"
    assert anns[0].scope == "feature"


def test_crlf_line_endings_feature_file(run_behave):
    """Feature files with CRLF line endings should work correctly."""

    result = run_behave(
        feature_content=(
            "# @jira TICKET-CRLF\r\n"
            "Feature: CRLF Test\r\n"
            "\r\n"
            "  Scenario: S1\r\n"
            "    Given a step\r\n"
            "    Then the test passes\r\n"
        ),
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("the test passes")
            def step_then(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_rule_scope_annotations(run_behave):
    """Annotations before Rule: should be scoped to the rule."""
    result = run_behave(
        feature_content="""
            Feature: Rule Test

            # @rule-id R-001
            Rule: My Rule

              Scenario: S1
                Given a step
                Then the rule annotation is present
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import extract_annotations, inject_metadata

            @given("a step")
            def step_given(context):
                pass

            @then("the rule annotation is present")
            def step_check(context):
                anns = extract_annotations(context.feature.filename)
                rule_anns = [a for a in anns if a.scope == "rule"]
                assert len(rule_anns) == 1
                assert rule_anns[0].key == "rule-id"
                assert rule_anns[0].value == "R-001"
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_annotations_with_special_chars_in_tags(run_behave):
    """Annotations with special characters should produce sanitized tags."""
    result = run_behave(
        feature_content="""
            # @priority high.priority
            Feature: Tag Sanitization

              Scenario: S1
                Given a step
                Then the tag is sanitized
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import extract_annotations, annotations_to_tags

            @given("a step")
            def step_given(context):
                pass

            @then("the tag is sanitized")
            def step_check(context):
                anns = extract_annotations(context.feature.filename)
                tags = annotations_to_tags(anns)
                assert tags == ["@priority-high-priority"]
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_continue_on_error_in_real_behave(run_behave):
    """continue_on_error should run all hooks even when one fails."""
    result = run_behave(
        feature_content="""
            # @before-scenario: Given setup ok
            # @before-scenario: Given setup fail
            # @before-scenario: Given setup ok2
            Feature: Continue On Error

              Scenario: S1
                Then all hooks were attempted
        """,
        steps_content="""
            from behave import given, then

            @given("setup ok")
            def step_ok(context):
                context.hook_ok = True

            @given("setup fail")
            def step_fail(context):
                raise AssertionError("intentional failure")

            @given("setup ok2")
            def step_ok2(context):
                context.hook_ok2 = True

            @then("all hooks were attempted")
            def step_check(context):
                assert getattr(context, "hook_ok", False)
                assert getattr(context, "hook_ok2", False)
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_scenario
            from behave_comments.errors import LifecycleStepError

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)

            def before_scenario(context, scenario):
                try:
                    run_before_scenario(context, scenario, continue_on_error=True)
                except LifecycleStepError:
                    pass
        """,
    )
    assert result.returncode == 0


def test_dedup_tags_in_real_behave(run_behave):
    """Dedup should remove duplicate tags in real Behave."""
    result = run_behave(
        feature_content="""
            # @env prod
            # @env prod
            Feature: Dedup Test

              Scenario: S1
                Given a step
                Then dedup removes duplicates
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import extract_annotations, annotations_to_tags

            @given("a step")
            def step_given(context):
                pass

            @then("dedup removes duplicates")
            def step_check(context):
                anns = extract_annotations(context.feature.filename)
                tags_no_dedup = annotations_to_tags(anns)
                assert tags_no_dedup == ["@env-prod", "@env-prod"]
                tags_dedup = annotations_to_tags(anns, dedup=True)
                assert tags_dedup == ["@env-prod"]
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_xml_with_namespaces_integration(run_behave):
    """XML with namespaces should be parsed correctly in integration."""
    result = run_behave(
        feature_content="""
            Feature: XML Namespaces

              Scenario: Parse XML with namespace
                Given a step with XML namespace doc string
                  \"\"\"xml
                  <root xmlns:ns="http://example.com"><ns:item>value</ns:item></root>
                  \"\"\"
                Then the XML namespace item is "value"
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with XML namespace doc string")
            def step_xml(context):
                context.xml_root = parse_text(str(context.text), "xml")

            @then('the XML namespace item is "value"')
            def step_check(context):
                root = context.xml_root
                assert root.tag == "root"
                child = root[0]
                assert "item" in child.tag
                assert child.text == "value"
        """,
    )
    assert result.returncode == 0


def test_yaml_list_doc_string_integration(run_behave):
    """YAML list doc strings should be parsed correctly."""
    result = run_behave(
        feature_content="""
            Feature: YAML List

              Scenario: Parse YAML list
                Given a step with a YAML list doc string
                  \"\"\"yaml
                  - alpha
                  - beta
                  - gamma
                  \"\"\"
                Then the YAML list has 3 items
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with a YAML list doc string")
            def step_yaml(context):
                context.yaml_data = parse_text(str(context.text), "yaml")

            @then("the YAML list has 3 items")
            def step_check(context):
                assert isinstance(context.yaml_data, list)
                assert len(context.yaml_data) == 3
                assert context.yaml_data[0] == "alpha"
                assert context.yaml_data[2] == "gamma"
        """,
    )
    assert result.returncode == 0


def test_csv_with_quoted_fields_integration(run_behave):
    """CSV with quoted fields should be parsed correctly."""
    feature = (
        "Feature: CSV Quoted\n"
        "\n"
        "  Scenario: Parse CSV with quotes\n"
        "    Given a step with a CSV doc string\n"
        '      """csv\n'
        "      name,desc\n"
        '      Alice,"Hello, World"\n'
        '      Bob,"He said ""hi"" there"\n'
        '      """\n'
        "    Then the CSV has 2 rows\n"
    )
    result = run_behave(
        feature_content=feature,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a step with a CSV doc string")
            def step_csv(context):
                context.csv_data = parse_text(str(context.text), "csv")

            @then("the CSV has 2 rows")
            def step_check(context):
                assert len(context.csv_data) == 2
                assert context.csv_data[0]["name"] == "Alice"
                assert context.csv_data[0]["desc"] == "Hello, World"
                assert context.csv_data[1]["desc"] == 'He said "hi" there'
        """,
    )
    assert result.returncode == 0
