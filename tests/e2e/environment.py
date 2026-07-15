"""Environment for E2E tests."""

from behave_comments import (
    inject_metadata,
    run_after_scenario,
    run_before_feature,
    setup_lifecycle_hooks,
)


def before_feature(context, feature):
    inject_metadata(context, feature)
    setup_lifecycle_hooks(context, feature)
    run_before_feature(context, feature)


def after_scenario(context, scenario):
    run_after_scenario(context, scenario)
