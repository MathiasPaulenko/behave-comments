"""Integration tests: lifecycle hooks with real Behave runs."""

from __future__ import annotations


def test_before_feature_hook_executes(run_behave):
    """A # @before-feature hook executes its step before the feature."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a clean database
            Feature: Lifecycle

              Scenario: Check setup
                Then the database was cleaned
        """,
        steps_content="""
            from behave import given, then

            @given("a clean database")
            def step_given_clean_db(context):
                context.db_cleaned = True

            @then("the database was cleaned")
            def step_then_db_clean(context):
                assert getattr(context, "db_cleaned", False), "Database was not cleaned"
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_after_scenario_hook_executes(run_behave):
    """A # @after-scenario hook executes its step after each scenario."""
    result = run_behave(
        feature_content="""
            Feature: After Scenario

              # @after-scenario: Then cleanup is done
              Scenario: First
                Given a step

              Scenario: Second
                Given a step
        """,
        steps_content="""
            from behave import given, then

            @given("a step")
            def step_given(context):
                pass

            @then("cleanup is done")
            def step_then_cleanup(context):
                context.cleanup_count = getattr(context, "cleanup_count", 0) + 1
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


def test_hook_step_not_found_fails(run_behave):
    """A hook referencing a non-existent step fails the feature."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given a nonexistent step
            Feature: Missing Step

              Scenario: Test
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
    combined = (result.stdout + result.stderr).lower()
    assert "not found" in combined or "undefined" in combined


def test_no_hooks_no_error(run_behave):
    """Feature without lifecycle hooks runs normally."""
    result = run_behave(
        feature_content="""
            Feature: No Hooks

              Scenario: Test
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
    assert result.returncode == 0


def test_multiple_hooks_same_type(run_behave):
    """Multiple before-feature hooks all execute in order."""
    result = run_behave(
        feature_content="""
            # @before-feature: Given step one
            # @before-feature: Given step two
            Feature: Multiple Hooks

              Scenario: Check both
                Then both steps ran
        """,
        steps_content="""
            from behave import given, then

            @given("step one")
            def step_given_one(context):
                context.step_one = True

            @given("step two")
            def step_given_two(context):
                context.step_two = True

            @then("both steps ran")
            def step_then_both(context):
                assert getattr(context, "step_one", False), "Step one did not run"
                assert getattr(context, "step_two", False), "Step two did not run"
        """,
        environment_content="""
            from behave_comments import setup_lifecycle_hooks, run_before_feature

            def before_feature(context, feature):
                setup_lifecycle_hooks(context, feature)
                run_before_feature(context, feature)
        """,
    )
    assert result.returncode == 0
