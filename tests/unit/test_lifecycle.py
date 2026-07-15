"""Tests for behave-comments lifecycle hooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from behave_comments.errors import LifecycleStepError
from behave_comments.lifecycle import (
    VALID_HOOKS,
    LifecycleHook,
    _execute_step,
    parse_lifecycle_hooks,
    parse_lifecycle_line,
    run_after_feature,
    run_after_scenario,
    run_after_step,
    run_before_feature,
    run_before_scenario,
    run_before_step,
    setup_lifecycle_hooks,
)
from tests.conftest import FakeContext, FakeFeature, FakeScenario, FakeStep


@pytest.mark.parametrize(
    ("line", "expected_hook_type", "expected_step_text"),
    [
        (
            "# @before-feature: Given the database is clean",
            "before-feature",
            "Given the database is clean",
        ),
        (
            "# @after-scenario: Then the cache is cleared",
            "after-scenario",
            "Then the cache is cleared",
        ),
        (
            "# @before-step: When the timer starts",
            "before-step",
            "When the timer starts",
        ),
        (
            "# @before-all: Given a clean state",
            "before-all",
            "Given a clean state",
        ),
        (
            "# @after-all: Then teardown is done",
            "after-all",
            "Then teardown is done",
        ),
        (
            "# @after-feature: Then the feature is done",
            "after-feature",
            "Then the feature is done",
        ),
        (
            "# @after-step: Then the step is done",
            "after-step",
            "Then the step is done",
        ),
    ],
)
def test_parse_lifecycle_line_valid(
    line: str, expected_hook_type: str, expected_step_text: str
) -> None:
    hook = parse_lifecycle_line(line, 1)
    assert hook is not None
    assert hook.hook_type == expected_hook_type
    assert hook.step_text == expected_step_text


@pytest.mark.parametrize(
    ("line", "expected_step_text"),
    [
        ("#  @before-feature:  Given x  ", "Given x"),
        ("#\t@before-scenario:\tGiven x", "Given x"),
    ],
)
def test_parse_lifecycle_line_whitespace(line: str, expected_step_text: str) -> None:
    hook = parse_lifecycle_line(line, 1)
    assert hook is not None
    assert hook.step_text == expected_step_text


def test_parse_lifecycle_line_step_text_with_quotes() -> None:
    hook = parse_lifecycle_line('# @before-feature: Given the user "Alice" exists', 1)
    assert hook is not None
    assert hook.step_text == 'Given the user "Alice" exists'


@pytest.mark.parametrize(
    "line",
    [
        "# @jira TICKET-1",
        "# This is a comment",
        "Given a step",
        "",
        "# @before-feature",
        "# @before-feature:",
    ],
)
def test_parse_lifecycle_line_not_hook(line: str) -> None:
    assert parse_lifecycle_line(line, 1) is None


@pytest.mark.parametrize(
    "line",
    [
        "# @before-invalid: Given x",
        "# @invalid-feature: Given x",
    ],
)
def test_parse_lifecycle_line_invalid_scope_or_hook(line: str) -> None:
    assert parse_lifecycle_line(line, 1) is None


def _write_feature(tmp_path, content: str):
    """Helper to write a .feature file in tmp_path."""
    path = tmp_path / "test.feature"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_lifecycle_hooks_multiple(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-feature: Given the database is clean\n"
        "Feature: Test\n"
        "# @after-scenario: Then the cache is cleared\n"
        "Scenario: S1\n"
        "# @before-step: When the timer starts\n"
        "Given x\n",
    )
    hooks = parse_lifecycle_hooks(str(path))
    assert len(hooks) == 3
    assert hooks[0].hook_type == "before-feature"
    assert hooks[1].hook_type == "after-scenario"
    assert hooks[2].hook_type == "before-step"


def test_parse_lifecycle_hooks_empty(tmp_path) -> None:
    path = _write_feature(tmp_path, "Feature: Test\nScenario: S1\nGiven x\n")
    hooks = parse_lifecycle_hooks(str(path))
    assert hooks == []


def test_parse_lifecycle_hooks_mixed_with_annotations(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @jira TICKET-1\n"
        "# @before-feature: Given the database is clean\n"
        "# @owner team-a\n"
        "Feature: Test\n",
    )
    hooks = parse_lifecycle_hooks(str(path))
    assert len(hooks) == 1
    assert hooks[0].hook_type == "before-feature"


def test_parse_lifecycle_line_line_number() -> None:
    hook = parse_lifecycle_line("# @before-feature: Given x", 5)
    assert hook is not None
    assert hook.line == 5


def test_lifecycle_hook_frozen() -> None:
    hook = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    with pytest.raises((AttributeError, TypeError)):
        hook.hook_type = "after-feature"  # type: ignore[misc]


def test_lifecycle_hook_slots() -> None:
    hook = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    with pytest.raises((AttributeError, TypeError)):
        hook.new_attr = 1  # type: ignore[attr-defined]


def test_valid_hooks_complete() -> None:
    assert frozenset(
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
    ) == VALID_HOOKS


class FakeMatch:
    """Minimal match-like object returned by registry.find_match."""

    __slots__ = ("_func",)

    def __init__(self, func: Callable[[Any], None]) -> None:
        self._func = func

    def run(self, context: Any) -> None:
        self._func(context)


class FakeRegistry:
    """Mimics Behave's StepRegistry for testing."""

    def __init__(self, steps: dict[str, Callable[[Any], None]] | None = None) -> None:
        self._steps = steps or {}

    def find_match(self, step: Any) -> FakeMatch | None:
        key = f"{step.step_type.capitalize()} {step.name}"
        if key in self._steps:
            return FakeMatch(self._steps[key])
        return None


def _patch_registry(monkeypatch, registry: FakeRegistry) -> None:
    """Patch behave.step_registry.registry with a FakeRegistry."""
    import behave.step_registry as mod

    monkeypatch.setattr(mod, "registry", registry)


def test_execute_step_success(monkeypatch) -> None:
    def step_given_x(context: Any) -> None:
        context.executed = True

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    _execute_step("Given x", context)
    assert context.executed is True


def test_execute_step_success_sets_value(monkeypatch) -> None:
    def step_then_y(context: Any) -> None:
        context.y = 42

    _patch_registry(monkeypatch, FakeRegistry({"Then y": step_then_y}))
    context = FakeContext()
    _execute_step("Then y", context)
    assert context.y == 42


def test_execute_step_not_found(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given nonexistent", context)
    assert exc_info.value.step_text == "Given nonexistent"
    assert "not found" in exc_info.value.detail


def test_execute_step_not_found_hook_type(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context, hook_type="before-feature")
    assert exc_info.value.hook_type == "before-feature"


def test_execute_step_failure(monkeypatch) -> None:
    def step_given_x(context: Any) -> None:
        raise AssertionError("db is dirty")

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context)
    assert exc_info.value.detail == "db is dirty"


def test_execute_step_failure_preserves_cause(monkeypatch) -> None:
    def step_given_x(context: Any) -> None:
        raise AssertionError("fail")

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context)
    assert isinstance(exc_info.value.__cause__, AssertionError)


def test_execute_step_registry_not_importable(monkeypatch) -> None:
    import sys

    monkeypatch.setitem(sys.modules, "behave.step_registry", None)
    monkeypatch.setitem(sys.modules, "behave.runner", None)
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context)
    assert "Could not import" in exc_info.value.detail


def test_execute_step_hook_type_in_error(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context, hook_type="before-feature")
    assert exc_info.value.hook_type == "before-feature"


def _write_feature(tmp_path, content: str):
    """Helper to write a .feature file in tmp_path."""
    path = tmp_path / "test.feature"
    path.write_text(content, encoding="utf-8")
    return path


def test_setup_lifecycle_hooks_basic(tmp_path) -> None:
    path = _write_feature(tmp_path, "# @before-feature: Given x\nFeature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    setup_lifecycle_hooks(context, feature)
    hooks = context._lifecycle_hooks
    assert len(hooks) == 1
    assert hooks[0].hook_type == "before-feature"


def test_setup_lifecycle_hooks_no_filename() -> None:
    context = FakeContext()
    feature = FakeFeature(filename=None)
    setup_lifecycle_hooks(context, feature)
    with pytest.raises(AttributeError):
        _ = context._lifecycle_hooks


def test_setup_lifecycle_hooks_no_hooks(tmp_path) -> None:
    path = _write_feature(tmp_path, "Feature: Test\n")
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    setup_lifecycle_hooks(context, feature)
    assert context._lifecycle_hooks == []


def test_run_before_feature_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_given_x(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given x", line=1),
    ]
    run_before_feature(context, FakeFeature())
    assert executed["value"] is True


def test_run_before_feature_wrong_type_not_executed(monkeypatch) -> None:
    executed = {"value": False}

    def step_then_y(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Then y": step_then_y}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-scenario", step_text="Then y", line=1),
    ]
    run_before_feature(context, FakeFeature())
    assert executed["value"] is False


def test_run_after_scenario_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_then_cleanup(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Then cleanup": step_then_cleanup}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-scenario", step_text="Then cleanup", line=1),
    ]
    run_after_scenario(context, FakeScenario())
    assert executed["value"] is True


def test_run_hooks_multiple_same_type(monkeypatch) -> None:
    calls = []

    def step_given_a(context: Any) -> None:
        calls.append("a")

    def step_given_b(context: Any) -> None:
        calls.append("b")

    _patch_registry(
        monkeypatch,
        FakeRegistry({"Given a": step_given_a, "Given b": step_given_b}),
    )
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given a", line=1),
        LifecycleHook(hook_type="before-feature", step_text="Given b", line=2),
    ]
    run_before_feature(context, FakeFeature())
    assert calls == ["a", "b"]


def test_run_hooks_filters_by_type(monkeypatch) -> None:
    calls = []

    def step_given_x(context: Any) -> None:
        calls.append("x")

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given x", line=1),
        LifecycleHook(hook_type="after-scenario", step_text="Given x", line=2),
        LifecycleHook(hook_type="before-step", step_text="Given x", line=3),
    ]
    run_before_feature(context, FakeFeature())
    assert calls == ["x"]


def test_run_hooks_no_setup() -> None:
    context = FakeContext()
    run_before_feature(context, FakeFeature())


def test_run_hooks_step_failure_propagates(monkeypatch) -> None:
    def step_given_x(context: Any) -> None:
        raise AssertionError("fail")

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given x", line=1),
    ]
    with pytest.raises(LifecycleStepError):
        run_before_feature(context, FakeFeature())


@pytest.mark.parametrize(
    ("run_func", "hook_type", "arg"),
    [
        (run_before_feature, "before-feature", FakeFeature()),
        (run_after_feature, "after-feature", FakeFeature()),
        (run_before_scenario, "before-scenario", FakeScenario()),
        (run_after_scenario, "after-scenario", FakeScenario()),
        (run_before_step, "before-step", FakeStep()),
        (run_after_step, "after-step", FakeStep()),
    ],
)
def test_run_functions_filter_by_type(
    monkeypatch,
    run_func: Callable[..., None],
    hook_type: str,
    arg: Any,
) -> None:
    calls = []

    def step_given_x(context: Any) -> None:
        calls.append(hook_type)

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type=hook_type, step_text="Given x", line=1),
        LifecycleHook(hook_type="other-type", step_text="Given x", line=2),
    ]
    run_func(context, arg)
    assert calls == [hook_type]
