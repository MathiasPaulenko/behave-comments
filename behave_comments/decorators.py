"""Decorators for behave-comments."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from behave_comments.parser import extract_text_block


def with_parsed_text(
    param_name: str = "text_block",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that extracts and injects a parsed text block into a step.

    The decorated step function receives a TextBlock as a keyword argument.

    Args:
        param_name: The name of the keyword argument to inject.
            Defaults to ``"text_block"``.

    Returns:
        A decorator function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(context: Any, *args: Any, **kwargs: Any) -> Any:
            # Behave calls step functions as func(context, *params): positional
            # args are step parameters, never the step object. A positional step
            # is only consumed when it quacks like one (has a ``text`` attr),
            # which keeps manual calls like ``func(context, step)`` working.
            step = kwargs.pop("step", None)
            if step is None and args and hasattr(args[0], "text"):
                step = args[0]
                args = args[1:]
            if step is None:
                step = context

            text_block = extract_text_block(step)
            if text_block is None:
                raise ValueError(
                    f"Step '{getattr(step, 'name', '<unknown>')}' has no text block. "
                    f"The @with_parsed_text decorator requires a doc string."
                )

            kwargs[param_name] = text_block
            return func(context, *args, **kwargs)

        return wrapper

    return decorator
