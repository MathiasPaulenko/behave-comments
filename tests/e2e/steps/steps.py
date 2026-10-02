"""Step definitions for E2E tests."""

from behave import given, then

from behave_comments import extract_text_block


def _block(context):
    context.block = extract_text_block(context)
    assert context.block is not None, "No text block extracted"


@given("a step with a JSON doc string")
def step_given_json(context):
    _block(context)


@then('the parsed name is "Alice"')
def step_then_name(context):
    assert context.block.content_type == "json"
    assert context.block.parsed == {"name": "Alice", "age": 30}


@given("a step with a CSV doc string")
def step_given_csv(context):
    _block(context)


@then("the CSV has 2 rows")
def step_then_csv_rows(context):
    assert context.block.content_type == "csv"
    assert context.block.parsed == [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
    ]


@given("a step with a plain text doc string")
def step_given_plain(context):
    _block(context)


@then('the text is "just plain text"')
def step_then_plain(context):
    assert context.block.content_type == "text/plain"
    assert context.block.parsed == "just plain text"


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
    _block(context)


@then('the YAML name is "Bob"')
def step_then_yaml_name(context):
    assert context.block.content_type == "yaml"
    assert context.block.parsed == {"name": "Bob", "age": 25}


@given("a step with an XML doc string")
def step_given_xml(context):
    _block(context)


@then('the XML item is "hello"')
def step_then_xml_item(context):
    assert context.block.content_type == "xml"
    assert context.block.parsed.find("item").text == "hello"


@given("a step with a form doc string")
def step_given_form(context):
    _block(context)


@then('the form key1 is "val1"')
def step_then_form_key1(context):
    assert context.block.content_type == "form-urlencoded"
    assert context.block.parsed["key1"] == ["val1"]


@given("a step with a GraphQL doc string")
def step_given_graphql(context):
    _block(context)


@then('the GraphQL query contains "hero"')
def step_then_graphql_hero(context):
    assert context.block.content_type == "graphql"
    assert "hero" in context.block.parsed


@given("a step with a CSV quoted doc string")
def step_given_csv_quoted(context):
    _block(context)


@then("the CSV quoted has 2 rows")
def step_then_csv_quoted_rows(context):
    assert context.block.content_type == "csv"
    assert context.block.parsed == [
        {"name": "Alice", "desc": "Hello, World"},
        {"name": "Bob", "desc": 'He said "hi" there'},
    ]


@given("a step with a YAML list doc string")
def step_given_yaml_list(context):
    _block(context)


@then("the YAML list has 3 items")
def step_then_yaml_list_3(context):
    assert context.block.content_type == "yaml"
    assert context.block.parsed == ["alpha", "beta", "gamma"]


@given("a step with an XML namespace doc string")
def step_given_xml_ns(context):
    _block(context)


@then('the XML namespace item is "value"')
def step_then_xml_ns_value(context):
    assert context.block.content_type == "xml"
    item = context.block.parsed.find("{http://example.com}item")
    assert item is not None and item.text == "value"


@then("dedup removes duplicate tags")
def step_then_dedup_tags(context):
    from behave_comments import annotations_to_tags, extract_annotations

    anns = extract_annotations(context.feature.filename)
    feature_anns = [a for a in anns if a.scope == "feature"]
    tags = annotations_to_tags(feature_anns, dedup=True)
    assert "@jira-TICKET-E2E" in tags
    assert tags.count("@jira-TICKET-E2E") == 1
