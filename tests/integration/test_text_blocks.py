"""Integration tests: text block parsing with real Behave runs."""

from __future__ import annotations


def test_json_text_block_parsed(run_behave):
    """A JSON doc string is available in the step via context.text."""
    result = run_behave(
        feature_content="""
            Feature: JSON Text Block

              Scenario: Parse JSON
                Given a JSON document
                  \"\"\"json
                  {"key": "value"}
                  \"\"\"
                Then the parsed value should be "value"
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a JSON document")
            def step_given_json(context):
                parsed = parse_text(str(context.text), "json")
                assert parsed == {"key": "value"}

            @then('the parsed value should be "value"')
            def step_then_value(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_text_block_with_decorator(run_behave):
    """The with_parsed_text decorator injects a TextBlock."""
    result = run_behave(
        feature_content="""
            Feature: Decorator Text Block

              Scenario: Use decorator
                Given a YAML document
                  \"\"\"yaml
                  key: value
                  \"\"\"
                Then the text block is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a YAML document")
            def step_given_yaml(context):
                parsed = parse_text(str(context.text), "yaml")
                assert parsed == {"key": "value"}

            @then("the text block is parsed")
            def step_then_parsed(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_csv_text_block(run_behave):
    """A CSV doc string is parsed into a list of dicts."""
    result = run_behave(
        feature_content="""
            Feature: CSV Text Block

              Scenario: Parse CSV
                Given a CSV document
                  \"\"\"csv
                  name,age
                  Alice,30
                  \"\"\"
                Then the CSV is parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a CSV document")
            def step_given_csv(context):
                parsed = parse_text(str(context.text), "csv")
                assert parsed == [{"name": "Alice", "age": "30"}]

            @then("the CSV is parsed")
            def step_then_csv(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_plain_text_block(run_behave):
    """A plain text doc string works without content type."""
    result = run_behave(
        feature_content="""
            Feature: Plain Text Block

              Scenario: Plain text
                Given a text document
                  \"\"\"
                  just text
                  \"\"\"
                Then the text is preserved
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import extract_text_block

            @given("a text document")
            def step_given_text(context):
                block = extract_text_block(context)
                assert block is not None
                assert block.content_type == "text/plain"
                assert block.content == "just text"

            @then("the text is preserved")
            def step_then_text(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_invalid_json_raises_error(run_behave):
    """Invalid JSON in a doc string causes a ParseError."""
    result = run_behave(
        feature_content="""
            Feature: Invalid JSON

              Scenario: Bad JSON
                Given a JSON document
                  \"\"\"json
                  {invalid}
                  \"\"\"
                Then the step fails
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import parse_text

            @given("a JSON document")
            def step_given_json(context):
                parse_text(str(context.text), "json")

            @then("the step fails")
            def step_then_fails(context):
                pass
        """,
    )
    assert result.returncode != 0
