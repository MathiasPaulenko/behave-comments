"""Step definitions for E2E tests."""

from behave import given, then


@given("a step with a JSON doc string")
def step_given_json(context):
    pass


@then('the parsed name is "Alice"')
def step_then_name(context):
    pass


@given("a step with a CSV doc string")
def step_given_csv(context):
    pass


@then("the CSV has 2 rows")
def step_then_csv_rows(context):
    pass


@given("a step with a plain text doc string")
def step_given_plain(context):
    pass


@then('the text is "just plain text"')
def step_then_plain(context):
    pass


@then("context has feature metadata")
def step_then_feature_meta(context):
    assert hasattr(context, "metadata"), "No metadata"
    assert "feature" in context.metadata, "No feature scope"
    anns = context.metadata["feature"]
    assert any(a["key"] == "jira" and a["value"] == "TICKET-100" for a in anns)


@then("context has scenario metadata")
def step_then_scenario_meta(context):
    assert "scenario" in context.metadata, "No scenario scope"
    anns = context.metadata["scenario"]
    assert any(a["key"] == "id" and a["value"] == "SC-001" for a in anns)


@given("a clean database")
def step_given_clean_db(context):
    context.db_cleaned = True


@then("the database was cleaned")
def step_then_db_clean(context):
    assert getattr(context, "db_cleaned", False), "DB not cleaned"


@given("a step")
def step_given_step(context):
    pass


@then("record cleanup")
def step_then_cleanup(context):
    context.cleanup_done = True
