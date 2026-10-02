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
            from behave_comments import with_parsed_text

            @given("a YAML document")
            @with_parsed_text()
            def step_given_yaml(context, text_block):
                assert text_block.content_type == "yaml"
                assert text_block.parsed == {"key": "value"}

            @then("the text block is parsed")
            def step_then_parsed(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_media_type_on_docstring_opening_line(run_behave):
    """A media type on the opening line (\"\"\"json) is recovered."""
    result = run_behave(
        feature_content="""
            Feature: Media Type Opening Line

              Scenario: Declared JSON
                Given a JSON document
                  \"\"\"json
                  {"key": "value"}
                  \"\"\"
                Then the JSON was parsed
        """,
        steps_content="""
            from behave import given, then
            from behave_comments import extract_text_block

            @given("a JSON document")
            def step_given_json(context):
                block = extract_text_block(context)
                assert block.content_type == "json"
                assert block.parsed == {"key": "value"}

            @then("the JSON was parsed")
            def step_then_parsed(context):
                pass
        """,
    )
    assert result.returncode == 0


def test_decorator_with_anonymous_step_parameter(run_behave):
    """with_parsed_text does not swallow positional step parameters."""
    result = run_behave(
        feature_content="""
            Feature: Decorator With Params

              Scenario: Anonymous param
                Given a document with 3 items
                  \"\"\"json
                  {"key": "value"}
                  \"\"\"
        """,
        steps_content="""
            from behave import given, use_step_matcher
            from behave_comments import with_parsed_text

            use_step_matcher("re")

            @given(r"a document with (\\d+) items")
            @with_parsed_text()
            def step_given_doc(context, count, text_block):
                assert count == "3"
                assert text_block.content_type == "json"
                assert text_block.parsed == {"key": "value"}
        """,
    )
    assert result.returncode == 0


def test_content_type_as_first_body_line(run_behave):
    """Content type as first line inside the doc string still works."""
    result = run_behave(
        feature_content="""
            Feature: Body Content Type

              Scenario: First line type
                Given a JSON document
                  \"\"\"
                  json
                  {"key": "value"}
                  \"\"\"
        """,
        steps_content="""
            from behave import given
            from behave_comments import extract_text_block

            @given("a JSON document")
            def step_given_json(context):
                block = extract_text_block(context)
                assert block.content_type == "json"
                assert block.parsed == {"key": "value"}
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
