"""Integration tests: annotation extraction with real Behave runs."""

from __future__ import annotations


def test_metadata_injected_in_before_feature(run_behave):
    """inject_metadata stores annotations in context.metadata."""
    result = run_behave(
        feature_content="""
            # @jira TICKET-42
            # @owner team-alpha
            Feature: Annotations

              Scenario: Check metadata
                Then context has metadata
        """,
        steps_content="""
            from behave import then

            @then("context has metadata")
            def step_then_metadata(context):
                assert hasattr(context, "metadata"), "No metadata in context"
                assert "feature" in context.metadata, "No feature scope"
                feature_anns = context.metadata["feature"]
                assert len(feature_anns) == 2, f"Expected 2, got {len(feature_anns)}"
                assert feature_anns[0]["key"] == "jira"
                assert feature_anns[0]["value"] == "TICKET-42"
                assert feature_anns[1]["key"] == "owner"
                assert feature_anns[1]["value"] == "team-alpha"
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_scenario_scope_annotations(run_behave):
    """Annotations before a Scenario get scope='scenario'."""
    result = run_behave(
        feature_content="""
            Feature: Scenario Scope

              # @id SC-001
              Scenario: Has annotation
                Then context has scenario metadata

              Scenario: No annotation
                Then context has one scenario metadata
        """,
        steps_content="""
            from behave import then

            @then("context has scenario metadata")
            def step_then_has(context):
                assert "scenario" in context.metadata
                anns = context.metadata["scenario"]
                assert len(anns) == 1
                assert anns[0]["key"] == "id"
                assert anns[0]["value"] == "SC-001"

            @then("context has one scenario metadata")
            def step_then_no(context):
                anns = context.metadata.get("scenario", [])
                assert len(anns) == 1, f"Expected 1, got {len(anns)}"
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0


def test_annotations_to_tags(run_behave):
    """annotations_to_tags converts annotations to Behave tags."""
    result = run_behave(
        feature_content="""
            # @smoke
            # @priority high
            Feature: Tags

              Scenario: Run with tags
                Then the test runs
        """,
        steps_content="""
            from behave import then

            @then("the test runs")
            def step_then_runs(context):
                pass
        """,
        environment_content="""
            from behave_comments import extract_annotations, annotations_to_tags

            def before_feature(context, feature):
                anns = extract_annotations(feature.filename)
                tags = annotations_to_tags(anns)
                feature.tags.extend(tags)
        """,
    )
    assert result.returncode == 0


def test_no_annotations_no_metadata(run_behave):
    """Feature without annotations has empty metadata."""
    result = run_behave(
        feature_content="""
            Feature: No Annotations

              Scenario: Test
                Then metadata is empty
        """,
        steps_content="""
            from behave import then

            @then("metadata is empty")
            def step_then_empty(context):
                assert hasattr(context, "metadata")
                assert context.metadata == {}
        """,
        environment_content="""
            from behave_comments import inject_metadata

            def before_feature(context, feature):
                inject_metadata(context, feature)
        """,
    )
    assert result.returncode == 0
