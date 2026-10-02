"""Declarative lifecycle hooks from .feature file comments."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from behave_comments.annotations import _iter_code_lines
from behave_comments.errors import LifecycleStepError

logger = logging.getLogger(__name__)

_LIFECYCLE_HOOK_RE = re.compile(
    r"^#\s*@(?P<hook>before|after)-(?P<scope>feature|scenario|step|all)\s*:\s*(?P<step>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class LifecycleHook:
    """A parsed lifecycle hook declaration.

    Attributes:
        hook_type: The hook type (e.g. "before-feature").
        step_text: The step text to execute (e.g. "Given the database is clean").
        line: The line number in the feature file.
        filename: The .feature file the hook was declared in, if known.
    """

    hook_type: str
    step_text: str
    line: int
    filename: str = ""


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

    hook_prefix = match.group("hook").lower()
    scope = match.group("scope").lower()
    step_text = match.group("step").strip()

    hook_type = f"{hook_prefix}-{scope}"

    return LifecycleHook(
        hook_type=hook_type,
        step_text=step_text,
        line=line_number,
    )


def parse_lifecycle_hooks(feature_path: str | Path) -> list[LifecycleHook]:
    """Extract all lifecycle hook declarations from a .feature file.

    Args:
        feature_path: Path to the .feature file.

    Returns:
        A list of LifecycleHook objects.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(feature_path)
    content = path.read_text(encoding="utf-8-sig")

    hooks: list[LifecycleHook] = []
    for line_number, line in _iter_code_lines(content):
        hook = parse_lifecycle_line(line, line_number)
        if hook is not None:
            hooks.append(
                LifecycleHook(
                    hook_type=hook.hook_type,
                    step_text=hook.step_text,
                    line=hook.line,
                    filename=str(path),
                )
            )

    return hooks


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
            return
        except Exception as e:
            if "outside of feature" in str(e).lower():
                pass
            else:
                raise LifecycleStepError(
                    hook_type=hook_type,
                    step_text=step_text,
                    detail=str(e),
                ) from e

    try:
        from behave.step_registry import registry as behave_registry
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
    if not filename:
        return

    hooks = parse_lifecycle_hooks(filename)
    context._lifecycle_hooks = hooks
    _merge_global_hooks(context, hooks)


def setup_lifecycle_hooks_from_path(
    context: Any,
    feature_path: str | Path,
) -> None:
    """Parse lifecycle hooks from a .feature file or directory.

    Use this from ``before_all`` / ``after_all`` in ``environment.py``,
    where the Behave ``feature`` object is not yet available. When given
    a directory, hooks are collected from every ``*.feature`` file in it
    (recursively), which is the only way ``before-all``/``after-all``
    hooks can work across multiple features.

    Args:
        context: Behave's context object.
        feature_path: Path to a .feature file or a directory containing them.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(feature_path)
    if path.is_dir():
        hooks = [
            hook for file in sorted(path.rglob("*.feature")) for hook in parse_lifecycle_hooks(file)
        ]
    else:
        hooks = parse_lifecycle_hooks(path)
    context._lifecycle_hooks = hooks
    _merge_global_hooks(context, hooks)


def _merge_global_hooks(context: Any, hooks: list[LifecycleHook]) -> None:
    """Accumulate ``*-all`` hooks so they survive per-feature overwrites.

    ``setup_lifecycle_hooks`` replaces ``context._lifecycle_hooks`` on every
    feature; without a separate store, ``after_all`` would only see the hooks
    of the last feature parsed. ``-all`` hooks are tracked globally instead.
    """
    global_hooks: list[LifecycleHook] | None = getattr(context, "_lifecycle_hooks_global", None)
    if global_hooks is None:
        global_hooks = []
        context._lifecycle_hooks_global = global_hooks
    for hook in hooks:
        if hook.hook_type.endswith("-all") and hook not in global_hooks:
            global_hooks.append(hook)


def _get_hooks(context: Any, hook_type: str) -> list[LifecycleHook]:
    """Retrieve stored lifecycle hooks of the given type from context."""
    hooks = [
        hook for hook in getattr(context, "_lifecycle_hooks", []) if hook.hook_type == hook_type
    ]
    if hook_type.endswith("-all"):
        for hook in getattr(context, "_lifecycle_hooks_global", []):
            if hook.hook_type == hook_type and hook not in hooks:
                hooks.append(hook)
    return hooks


def _run_hooks(
    context: Any,
    hook_type: str,
    *,
    continue_on_error: bool = False,
) -> None:
    """Execute all lifecycle hooks of the given type.

    Args:
        context: Behave's context object.
        hook_type: The hook type to execute (e.g. "before-feature").
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Errors are logged and a single combined
            ``LifecycleStepError`` is raised after all hooks run.
            If False (default), the first error stops execution.
    """
    hooks = _get_hooks(context, hook_type)
    errors: list[LifecycleStepError] = []
    for hook in hooks:
        try:
            _execute_step(hook.step_text, context, hook_type=hook_type)
        except LifecycleStepError as e:
            if not continue_on_error:
                raise
            logger.error("Hook %s failed: %s", hook_type, e)
            errors.append(e)
    if errors:
        details = "; ".join(str(e) for e in errors)
        raise LifecycleStepError(
            hook_type=hook_type,
            step_text=f"{len(errors)} hook(s) failed",
            detail=details,
        )


def run_before_feature(
    context: Any,
    feature: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run before-feature lifecycle hooks. Call from ``before_feature``.

    Args:
        context: Behave's context object.
        feature: The Behave feature object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "before-feature", continue_on_error=continue_on_error)


def run_after_feature(
    context: Any,
    feature: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run after-feature lifecycle hooks. Call from ``after_feature``.

    Args:
        context: Behave's context object.
        feature: The Behave feature object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "after-feature", continue_on_error=continue_on_error)


def run_before_scenario(
    context: Any,
    scenario: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run before-scenario lifecycle hooks. Call from ``before_scenario``.

    Args:
        context: Behave's context object.
        scenario: The Behave scenario object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "before-scenario", continue_on_error=continue_on_error)


def run_after_scenario(
    context: Any,
    scenario: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run after-scenario lifecycle hooks. Call from ``after_scenario``.

    Args:
        context: Behave's context object.
        scenario: The Behave scenario object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "after-scenario", continue_on_error=continue_on_error)


def run_before_step(
    context: Any,
    step: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run before-step lifecycle hooks. Call from ``before_step``.

    Args:
        context: Behave's context object.
        step: The Behave step object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "before-step", continue_on_error=continue_on_error)


def run_after_step(
    context: Any,
    step: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run after-step lifecycle hooks. Call from ``after_step``.

    Args:
        context: Behave's context object.
        step: The Behave step object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "after-step", continue_on_error=continue_on_error)


def run_before_all(
    context: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run before-all lifecycle hooks. Call from ``before_all``.

    Args:
        context: Behave's context object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "before-all", continue_on_error=continue_on_error)


def run_after_all(
    context: Any,
    *,
    continue_on_error: bool = False,
) -> None:
    """Run after-all lifecycle hooks. Call from ``after_all``.

    Args:
        context: Behave's context object.
        continue_on_error: If True, continue executing remaining hooks
            when one fails. Defaults to False.
    """
    _run_hooks(context, "after-all", continue_on_error=continue_on_error)
