"""Tests for behave-comments decorators."""

from __future__ import annotations

from typing import Any

import pytest

from behave_comments.decorators import with_parsed_text
from behave_comments.models import TextBlock
from tests.conftest import FakeStep


def test_with_parsed_text_json() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "json"
    assert result.parsed == {"k": "v"}


def test_with_parsed_text_yaml() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="yaml\nkey: value")
    result = step_func(context, step)
    assert result is not None
    assert result.parsed == {"key": "value"}


def test_with_parsed_text_plain() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="just text")
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "text/plain"
    assert result.parsed == "just text"


def test_with_parsed_text_custom_param_name_data() -> None:
    @with_parsed_text(param_name="data")
    def step_func(context: Any, data: TextBlock | None = None) -> TextBlock:
        return data

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(context, step)
    assert result is not None
    assert result.parsed == {"k": "v"}


def test_with_parsed_text_custom_param_name_payload() -> None:
    @with_parsed_text(param_name="payload")
    def step_func(context: Any, payload: TextBlock | None = None) -> TextBlock:
        return payload

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(context, step)
    assert result is not None
    assert result.parsed == {"k": "v"}


@pytest.mark.parametrize(
    "step",
    [
        FakeStep(text=None),
        FakeStep(text=""),
    ],
)
def test_with_parsed_text_no_text_block_raises(step: FakeStep) -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    with pytest.raises(ValueError, match="has no text block"):
        step_func(context, step)


def test_with_parsed_text_preserves_name() -> None:
    @with_parsed_text()
    def my_step(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        """My step docstring."""
        return text_block

    assert my_step.__name__ == "my_step"


def test_with_parsed_text_preserves_docstring() -> None:
    @with_parsed_text()
    def my_step(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        """My step docstring."""
        return text_block

    assert my_step.__doc__ == "My step docstring."


def test_with_parsed_text_receives_context() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> Any:
        return context

    sentinel = object()
    step = FakeStep(text='json\n{"k": "v"}')
    assert step_func(sentinel, step) is sentinel


def test_with_parsed_text_step_as_keyword() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(context, step=step)
    assert result is not None
    assert result.parsed == {"k": "v"}


def test_with_parsed_text_step_from_args() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(context, step)
    assert result is not None
    assert result.parsed == {"k": "v"}


def test_with_parsed_text_preserves_other_args() -> None:
    @with_parsed_text()
    def step_func(
        context: Any,
        other_arg: str = "",
        text_block: TextBlock | None = None,
    ) -> tuple[str, TextBlock]:
        return other_arg, text_block

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    other, tb = step_func(context, step, "hello")
    assert other == "hello"
    assert tb is not None
    assert tb.parsed == {"k": "v"}


def test_with_parsed_text_context_only() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    step = FakeStep(text='json\n{"k": "v"}')
    result = step_func(step)
    assert result is not None
    assert result.parsed == {"k": "v"}


# ---------------------------------------------------------------------------
# Edge cases: all content types through decorator
# ---------------------------------------------------------------------------


def test_with_parsed_text_xml() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="xml\n<root><child>text</child></root>")
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "xml"
    assert result.parsed.tag == "root"


def test_with_parsed_text_csv() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="csv\nname,age\nAlice,30")
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "csv"
    assert result.parsed == [{"name": "Alice", "age": "30"}]


def test_with_parsed_text_graphql() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="graphql\nquery { user { name } }")
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "graphql"
    assert result.parsed == "query { user { name } }"


def test_with_parsed_text_form_urlencoded() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="form-urlencoded\nkey=value&other=2")
    result = step_func(context, step)
    assert result is not None
    assert result.content_type == "form-urlencoded"
    assert result.parsed == {"key": ["value"], "other": ["2"]}


def test_with_parsed_text_step_without_name_attr() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()

    class StepNoName:
        text = 'json\n{"k": "v"}'

    result = step_func(context, StepNoName())
    assert result is not None
    assert result.parsed == {"k": "v"}


def test_with_parsed_text_no_text_block_error_message_contains_step_name() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text=None, name="my step")
    with pytest.raises(ValueError, match="my step"):
        step_func(context, step)


def test_with_parsed_text_preserves_other_kwargs() -> None:
    @with_parsed_text()
    def step_func(
        context: Any,
        other: str = "",
        text_block: TextBlock | None = None,
    ) -> tuple[str, TextBlock | None]:
        return other, text_block

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    other, tb = step_func(context, step, other="hello")
    assert other == "hello"
    assert tb is not None
    assert tb.parsed == {"k": "v"}


def test_with_parsed_text_returns_function_result() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> int:
        return 42

    context = object()
    step = FakeStep(text='json\n{"k": "v"}')
    assert step_func(context, step) == 42


def test_with_parsed_text_multiline_text() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text='json\n{\n  "key": "value",\n  "num": 42\n}')
    result = step_func(context, step)
    assert result is not None
    assert result.parsed == {"key": "value", "num": 42}


def test_with_parsed_text_empty_json_raises() -> None:
    @with_parsed_text()
    def step_func(context: Any, text_block: TextBlock | None = None) -> TextBlock:
        return text_block

    context = object()
    step = FakeStep(text="json\n")
    with pytest.raises(Exception):
        step_func(context, step)
