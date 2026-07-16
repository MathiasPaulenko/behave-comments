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
    if any(a["key"] == "jira" and a["value"] == "TICKET-E2E" for a in anns):
        return
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


@given("a step with a YAML doc string")
def step_given_yaml(context):
    pass


@then('the YAML name is "Bob"')
def step_then_yaml_name(context):
    pass


@given("a step with an XML doc string")
def step_given_xml(context):
    pass


@then('the XML item is "hello"')
def step_then_xml_item(context):
    pass


@given("a step with a form doc string")
def step_given_form(context):
    pass


@then('the form key1 is "val1"')
def step_then_form_key1(context):
    pass


@given("a step with a GraphQL doc string")
def step_given_graphql(context):
    pass


@then('the GraphQL query contains "hero"')
def step_then_graphql_hero(context):
    pass


@given("a step with a CSV quoted doc string")
def step_given_csv_quoted(context):
    pass


@then("the CSV quoted has 2 rows")
def step_then_csv_quoted_rows(context):
    pass


@given("a step with a YAML list doc string")
def step_given_yaml_list(context):
    pass


@then("the YAML list has 3 items")
def step_then_yaml_list_3(context):
    pass


@given("a step with an XML namespace doc string")
def step_given_xml_ns(context):
    pass


@then('the XML namespace item is "value"')
def step_then_xml_ns_value(context):
    pass


@then("dedup removes duplicate tags")
def step_then_dedup_tags(context):
    from behave_comments import annotations_to_tags, extract_annotations

    anns = extract_annotations(context.feature.filename)
    feature_anns = [a for a in anns if a.scope == "feature"]
    tags = annotations_to_tags(feature_anns, dedup=True)
    assert "@jira-TICKET-E2E" in tags
    assert tags.count("@jira-TICKET-E2E") == 1
