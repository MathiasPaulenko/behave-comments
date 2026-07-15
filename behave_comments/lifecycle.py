"""Declarative lifecycle hooks from .feature file comments."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from behave_comments.errors import LifecycleStepError

_LIFECYCLE_HOOK_RE = re.compile(
    r"^#\s*@(?P<hook>before|after)-(?P<scope>feature|scenario|step|all)\s*:\s*(?P<step>.+)$"
)

VALID_HOOKS: frozenset[str] = frozenset(
    {
        "before-feature",
        "before-scenario",
        "before-step",
        "before-all",
        "after-feature",
        "after-scenario",
        "after-step",
        "after-all",
    }
)


@dataclass(frozen=True, slots=True)
class LifecycleHook:
    """A parsed lifecycle hook declaration.

    Attributes:
        hook_type: The hook type (e.g. "before-feature").
        step_text: The step text to execute (e.g. "Given the database is clean").
        line: The line number in the feature file.
    """

    hook_type: str
    step_text: str
    line: int


def parse_lifecycle_line(line: str, line_number: int) -> LifecycleHook | None:
    """Parse a single comment line as a lifecycle hook.

    Supports syntax:
        # @before-feature: Given the database is clean
        # @after-scenario: Then the cache is cleared

    Args:
        line: The comment line to parse.
        line_number: The line number in the file.

    Returns:
        A LifecycleHook if the line is a valid hook declaration, or None
        if the line is not a lifecycle hook comment.
    """
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None

    match = _LIFECYCLE_HOOK_RE.match(stripped)
    if match is None:
        return None

    hook_prefix = match.group("hook")
    scope = match.group("scope")
    step_text = match.group("step").strip()

    hook_type = f"{hook_prefix}-{scope}"

    return LifecycleHook(
        hook_type=hook_type,
        step_text=step_text,
        line=line_number,
    )


def parse_lifecycle_hooks(feature_path: str) -> list[LifecycleHook]:
    """Extract all lifecycle hook declarations from a .feature file.

    Args:
        feature_path: Path to the .feature file.

    Returns:
        A list of LifecycleHook objects.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    from pathlib import Path

    path = Path(feature_path)
    content = path.read_text(encoding="utf-8")

    hooks: list[LifecycleHook] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        hook = parse_lifecycle_line(line, line_number)
        if hook is not None:
            hooks.append(hook)

    return hooks


logger = logging.getLogger(__name__)


_STEP_TYPE_RE = re.compile(r"^(?P<step_type>Given|When|Then|Step)\s+(?P<name>.+)$", re.IGNORECASE)


class _SimpleStep:
    """Minimal step-like object for registry.find_match."""

    __slots__ = ("step_type", "name")

    def __init__(self, step_type: str, name: str) -> None:
        self.step_type = step_type
        self.name = name


def _execute_step(
    step_text: str,
    context: Any,
    *,
    hook_type: str = "",
) -> None:
    """Execute a declarative step using Behave's step registry.

    Looks up the step in Behave's registry and invokes it with the
    provided context.

    Args:
        step_text: The step text (e.g. "Given the database is clean").
        context: Behave's context object.
        hook_type: The hook type for error messages (e.g. "before-feature").

    Raises:
        LifecycleStepError: If the step cannot be found or execution fails.
    """
    execute_steps = getattr(context, "execute_steps", None)
    if callable(execute_steps):
        try:
            execute_steps(step_text)
        except AssertionError as e:
            raise LifecycleStepError(
                hook_type=hook_type,
                step_text=step_text,
                detail=str(e),
            ) from e
        except Exception as e:
            raise LifecycleStepError(
                hook_type=hook_type,
                step_text=step_text,
                detail=str(e),
            ) from e
        return

    try:
        from behave.step_registry import registry as behave_registry
    except ImportError:
        try:
            from behave.runner import registry as behave_registry
        except ImportError:
            raise LifecycleStepError(
                hook_type=hook_type,
                step_text=step_text,
                detail="Could not import Behave's step registry",
            ) from None

    match_obj = _STEP_TYPE_RE.match(step_text)
    if match_obj is None:
        raise LifecycleStepError(
            hook_type=hook_type,
            step_text=step_text,
            detail="Step text must start with Given, When, Then, or Step.",
        )

    step = _SimpleStep(
        step_type=match_obj.group("step_type").lower(),
        name=match_obj.group("name"),
    )

    result = behave_registry.find_match(step)
    if result is None:
        raise LifecycleStepError(
            hook_type=hook_type,
            step_text=step_text,
            detail="Step not found in registry. Ensure the step is defined.",
        )

    try:
        result.run(context)
    except Exception as e:
        raise LifecycleStepError(
            hook_type=hook_type,
            step_text=step_text,
            detail=str(e),
        ) from e


def setup_lifecycle_hooks(
    context: Any,
    feature: Any,
) -> None:
    """Parse lifecycle hooks from the feature file and store them in context.

    Call this from ``before_feature`` in ``environment.py``.

    Args:
        context: Behave's context object.
        feature: The Behave feature object (must have ``filename``).
    """
    filename = getattr(feature, "filename", None)
    if filename is None:
        return

    hooks = parse_lifecycle_hooks(filename)
    context._lifecycle_hooks = hooks


def _get_hooks(context: Any) -> list[LifecycleHook]:
    """Retrieve stored lifecycle hooks from context."""
    return getattr(context, "_lifecycle_hooks", [])


def _run_hooks(
    context: Any,
    hook_type: str,
) -> None:
    """Execute all lifecycle hooks of the given type.

    Args:
        context: Behave's context object.
        hook_type: The hook type to execute (e.g. "before-feature").
    """
    hooks = _get_hooks(context)
    for hook in hooks:
        if hook.hook_type == hook_type:
            _execute_step(hook.step_text, context, hook_type=hook_type)


def run_before_feature(context: Any, feature: Any) -> None:
    """Run before-feature lifecycle hooks. Call from ``before_feature``."""
    _run_hooks(context, "before-feature")


def run_after_feature(context: Any, feature: Any) -> None:
    """Run after-feature lifecycle hooks. Call from ``after_feature``."""
    _run_hooks(context, "after-feature")


def run_before_scenario(context: Any, scenario: Any) -> None:
    """Run before-scenario lifecycle hooks. Call from ``before_scenario``."""
    _run_hooks(context, "before-scenario")


def run_after_scenario(context: Any, scenario: Any) -> None:
    """Run after-scenario lifecycle hooks. Call from ``after_scenario``."""
    _run_hooks(context, "after-scenario")


def run_before_step(context: Any, step: Any) -> None:
    """Run before-step lifecycle hooks. Call from ``before_step``."""
    _run_hooks(context, "before-step")


def run_after_step(context: Any, step: Any) -> None:
    """Run after-step lifecycle hooks. Call from ``after_step``."""
    _run_hooks(context, "after-step")
