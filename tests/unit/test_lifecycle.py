"""Tests for behave-comments lifecycle hooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from behave_comments.errors import LifecycleStepError
from behave_comments.lifecycle import (
    LifecycleHook,
    _execute_step,
    parse_lifecycle_hooks,
    parse_lifecycle_line,
    run_after_all,
    run_after_feature,
    run_after_scenario,
    run_after_step,
    run_before_all,
    run_before_feature,
    run_before_scenario,
    run_before_step,
    setup_lifecycle_hooks,
    setup_lifecycle_hooks_from_path,
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


def test_run_hooks_continue_on_error_runs_all_hooks(monkeypatch) -> None:
    calls = []

    def step_given_fail(context: Any) -> None:
        calls.append("fail")
        raise AssertionError("fail")

    def step_given_ok(context: Any) -> None:
        calls.append("ok")

    _patch_registry(
        monkeypatch,
        FakeRegistry({"Given fail": step_given_fail, "Given ok": step_given_ok}),
    )
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given fail", line=1),
        LifecycleHook(hook_type="before-feature", step_text="Given ok", line=2),
    ]
    with pytest.raises(LifecycleStepError) as exc_info:
        run_before_feature(context, FakeFeature(), continue_on_error=True)
    assert calls == ["fail", "ok"]
    assert "2 hook(s) failed" not in exc_info.value.step_text
    assert "1 hook(s) failed" in exc_info.value.step_text


def test_run_hooks_continue_on_error_multiple_failures(monkeypatch) -> None:
    def step_given_fail1(context: Any) -> None:
        raise AssertionError("fail1")

    def step_given_fail2(context: Any) -> None:
        raise AssertionError("fail2")

    _patch_registry(
        monkeypatch,
        FakeRegistry({"Given fail1": step_given_fail1, "Given fail2": step_given_fail2}),
    )
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-scenario", step_text="Given fail1", line=1),
        LifecycleHook(hook_type="after-scenario", step_text="Given fail2", line=2),
    ]
    with pytest.raises(LifecycleStepError) as exc_info:
        run_after_scenario(context, FakeScenario(), continue_on_error=True)
    assert "2 hook(s) failed" in exc_info.value.step_text
    assert "fail1" in exc_info.value.detail
    assert "fail2" in exc_info.value.detail


def test_run_hooks_continue_on_error_no_failures(monkeypatch) -> None:
    calls = []

    def step_given_ok(context: Any) -> None:
        calls.append("ok")

    _patch_registry(monkeypatch, FakeRegistry({"Given ok": step_given_ok}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-all", step_text="Given ok", line=1),
        LifecycleHook(hook_type="before-all", step_text="Given ok", line=2),
    ]
    run_before_all(context, continue_on_error=True)
    assert calls == ["ok", "ok"]


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


# ---------------------------------------------------------------------------
# Edge cases: _execute_step with context.execute_steps()
# ---------------------------------------------------------------------------


class FakeContextWithExecuteSteps(FakeContext):
    """FakeContext that has execute_steps, simulating real Behave."""

    def __init__(self, execute_steps_impl: Callable[[str], None]) -> None:
        super().__init__()
        self._execute_steps_impl = execute_steps_impl

    def execute_steps(self, step_text: str) -> None:
        self._execute_steps_impl(step_text)


def test_execute_step_uses_context_execute_steps_success() -> None:
    called = {"step": ""}

    def impl(step_text: str) -> None:
        called["step"] = step_text

    context = FakeContextWithExecuteSteps(impl)
    _execute_step("Given a clean database", context)
    assert called["step"] == "Given a clean database"


def test_execute_step_context_execute_steps_assertion_error(monkeypatch) -> None:
    def impl(step_text: str) -> None:
        raise AssertionError("step failed")

    context = FakeContextWithExecuteSteps(impl)
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context, hook_type="before-feature")
    assert exc_info.value.hook_type == "before-feature"
    assert "step failed" in exc_info.value.detail
    assert isinstance(exc_info.value.__cause__, AssertionError)


def test_execute_step_context_execute_steps_generic_exception(monkeypatch) -> None:
    def impl(step_text: str) -> None:
        raise ValueError("unexpected error")

    context = FakeContextWithExecuteSteps(impl)
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given x", context, hook_type="after-scenario")
    assert "unexpected error" in exc_info.value.detail
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_execute_step_invalid_step_prefix_no_execute_steps(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("do something", context, hook_type="before-feature")
    assert "must start with" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Edge cases: run_after_feature and run_before_scenario execution
# ---------------------------------------------------------------------------


def test_run_after_feature_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_then_done(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Then done": step_then_done}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-feature", step_text="Then done", line=1),
    ]
    run_after_feature(context, FakeFeature())
    assert executed["value"] is True


def test_run_before_scenario_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_given_setup(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Given setup": step_given_setup}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-scenario", step_text="Given setup", line=1),
    ]
    run_before_scenario(context, FakeScenario())
    assert executed["value"] is True


def test_run_before_step_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_given_init(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Given init": step_given_init}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-step", step_text="Given init", line=1),
    ]
    run_before_step(context, FakeStep())
    assert executed["value"] is True


def test_run_after_step_executes(monkeypatch) -> None:
    executed = {"value": False}

    def step_then_teardown(context: Any) -> None:
        executed["value"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Then teardown": step_then_teardown}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-step", step_text="Then teardown", line=1),
    ]
    run_after_step(context, FakeStep())
    assert executed["value"] is True


# ---------------------------------------------------------------------------
# Edge cases: parse_lifecycle_hooks with mixed content
# ---------------------------------------------------------------------------


def test_parse_lifecycle_hooks_mixed_with_annotations(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @jira TICKET-1\n"
        "# @before-feature: Given a clean database\n"
        "Feature: Test\n"
        "# @after-scenario: Then cleanup\n"
        "Scenario: S1\n"
        "    Given a step\n",
    )
    hooks = parse_lifecycle_hooks(path)
    assert len(hooks) == 2
    assert hooks[0].hook_type == "before-feature"
    assert hooks[0].step_text == "Given a clean database"
    assert hooks[1].hook_type == "after-scenario"
    assert hooks[1].step_text == "Then cleanup"


def test_parse_lifecycle_hooks_all_hook_types(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-all: Given global setup\n"
        "# @before-feature: Given feature setup\n"
        "# @before-scenario: Given scenario setup\n"
        "# @before-step: Given step setup\n"
        "# @after-step: Then step teardown\n"
        "# @after-scenario: Then scenario teardown\n"
        "# @after-feature: Then feature teardown\n"
        "# @after-all: Then global teardown\n"
        "Feature: Test\n"
        "Scenario: S1\n"
        "    Given a step\n",
    )
    hooks = parse_lifecycle_hooks(path)
    assert len(hooks) == 8
    hook_types = [h.hook_type for h in hooks]
    assert "before-all" in hook_types
    assert "before-feature" in hook_types
    assert "before-scenario" in hook_types
    assert "before-step" in hook_types
    assert "after-step" in hook_types
    assert "after-scenario" in hook_types
    assert "after-feature" in hook_types
    assert "after-all" in hook_types


def test_parse_lifecycle_hooks_empty_file(tmp_path) -> None:
    path = _write_feature(tmp_path, "")
    hooks = parse_lifecycle_hooks(path)
    assert hooks == []


def test_parse_lifecycle_hooks_only_feature_keyword(tmp_path) -> None:
    path = _write_feature(tmp_path, "Feature: Test\n")
    hooks = parse_lifecycle_hooks(path)
    assert hooks == []


# ---------------------------------------------------------------------------
# Edge cases: LifecycleHook dataclass, Step prefix, colons in step text
# ---------------------------------------------------------------------------


def test_lifecycle_hook_is_frozen() -> None:
    import dataclasses

    hook = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        hook.hook_type = "after-feature"  # type: ignore[misc]


def test_lifecycle_hook_eq() -> None:
    a = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    b = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    assert a == b


def test_lifecycle_hook_ne() -> None:
    a = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    b = LifecycleHook(hook_type="after-feature", step_text="Given x", line=1)
    assert a != b


def test_lifecycle_hook_repr() -> None:
    hook = LifecycleHook(hook_type="before-feature", step_text="Given x", line=1)
    r = repr(hook)
    assert "LifecycleHook" in r
    assert "before-feature" in r
    assert "Given x" in r


def test_parse_lifecycle_line_step_text_with_colons() -> None:
    hook = parse_lifecycle_line(
        "# @before-feature: Given the user: Alice exists", 1
    )
    assert hook is not None
    assert hook.step_text == "Given the user: Alice exists"


def test_parse_lifecycle_line_step_text_with_special_chars() -> None:
    hook = parse_lifecycle_line(
        "# @after-scenario: Then the value is $42.00 (USD)", 1
    )
    assert hook is not None
    assert hook.step_text == "Then the value is $42.00 (USD)"


def test_parse_lifecycle_line_step_text_with_given_lowercase() -> None:
    hook = parse_lifecycle_line("# @before-feature: given the database is clean", 1)
    assert hook is not None
    assert hook.hook_type == "before-feature"
    assert hook.step_text == "given the database is clean"


def test_parse_lifecycle_line_line_number_preserved() -> None:
    hook = parse_lifecycle_line("# @before-feature: Given x", 42)
    assert hook is not None
    assert hook.line == 42


def test_parse_lifecycle_hooks_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        parse_lifecycle_hooks("nonexistent.feature")


def test_parse_lifecycle_hooks_preserves_order(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-feature: Given A\n"
        "# @before-scenario: Given B\n"
        "# @after-scenario: Then C\n"
        "# @after-feature: Then D\n"
        "Feature: Test\n"
        "Scenario: S1\n"
        "    Given x\n",
    )
    hooks = parse_lifecycle_hooks(path)
    assert len(hooks) == 4
    assert hooks[0].step_text == "Given A"
    assert hooks[1].step_text == "Given B"
    assert hooks[2].step_text == "Then C"
    assert hooks[3].step_text == "Then D"


def test_parse_lifecycle_hooks_with_regular_comments(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# This is a regular comment\n"
        "# @jira TICKET-1\n"
        "# @before-feature: Given x\n"
        "# Another comment\n"
        "Feature: Test\n"
        "Scenario: S1\n"
        "    Given x\n",
    )
    hooks = parse_lifecycle_hooks(path)
    assert len(hooks) == 1
    assert hooks[0].hook_type == "before-feature"


def test_parse_lifecycle_hooks_duplicate_hooks(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-feature: Given A\n"
        "# @before-feature: Given B\n"
        "Feature: Test\n"
        "Scenario: S1\n"
        "    Given x\n",
    )
    hooks = parse_lifecycle_hooks(path)
    assert len(hooks) == 2
    assert all(h.hook_type == "before-feature" for h in hooks)


def test_setup_lifecycle_hooks_with_multiple_hook_types(tmp_path) -> None:
    path = _write_feature(
        tmp_path,
        "# @before-feature: Given A\n"
        "# @after-scenario: Then B\n"
        "Feature: Test\n"
        "Scenario: S1\n"
        "    Given x\n",
    )
    context = FakeContext()
    feature = FakeFeature(filename=str(path))
    setup_lifecycle_hooks(context, feature)
    hooks = context._lifecycle_hooks
    assert len(hooks) == 2
    assert hooks[0].hook_type == "before-feature"
    assert hooks[1].hook_type == "after-scenario"


def test_run_hooks_no_hooks_set_on_context() -> None:
    context = FakeContext()
    run_before_feature(context, FakeFeature())
    run_after_feature(context, FakeFeature())
    run_before_scenario(context, FakeScenario())
    run_after_scenario(context, FakeScenario())
    run_before_step(context, FakeStep())
    run_after_step(context, FakeStep())


def test_run_before_all_no_hooks() -> None:
    context = FakeContext()
    run_before_all(context)


def test_run_after_all_no_hooks() -> None:
    context = FakeContext()
    run_after_all(context)


def test_run_before_all_executes_hooks() -> None:
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-all", step_text="Given global setup", line=1),
        LifecycleHook(hook_type="before-feature", step_text="Given feature setup", line=2),
    ]
    context.execute_steps = lambda text: context._attrs.setdefault("executed", []).append(text)
    run_before_all(context)
    assert "Given global setup" in context.executed
    assert "Given feature setup" not in context.executed


def test_run_after_all_executes_hooks() -> None:
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="after-all", step_text="Then global teardown", line=1),
        LifecycleHook(hook_type="after-feature", step_text="Then feature teardown", line=2),
    ]
    context.execute_steps = lambda text: context._attrs.setdefault("executed", []).append(text)
    run_after_all(context)
    assert "Then global teardown" in context.executed
    assert "Then feature teardown" not in context.executed


def test_setup_lifecycle_hooks_from_path(tmp_path) -> None:
    feature_file = tmp_path / "test.feature"
    feature_file.write_text(
        "# @before-all: Given global setup\n"
        "# @after-all: Then global teardown\n"
        "Feature: Test\n",
        encoding="utf-8",
    )
    context = FakeContext()
    setup_lifecycle_hooks_from_path(context, str(feature_file))
    hooks = getattr(context, "_lifecycle_hooks", None)
    assert hooks is not None
    assert len(hooks) == 2
    assert hooks[0].hook_type == "before-all"
    assert hooks[1].hook_type == "after-all"


def test_setup_lifecycle_hooks_from_path_then_run_before_all(tmp_path) -> None:
    feature_file = tmp_path / "test.feature"
    feature_file.write_text(
        "# @before-all: Given global setup\n"
        "Feature: Test\n",
        encoding="utf-8",
    )
    context = FakeContext()
    setup_lifecycle_hooks_from_path(context, str(feature_file))
    context.execute_steps = lambda text: context._attrs.setdefault("executed", []).append(text)
    run_before_all(context)
    assert "Given global setup" in context.executed


def test_parse_lifecycle_line_case_insensitive() -> None:
    hook = parse_lifecycle_line("# @BEFORE-FEATURE: Given step", 1)
    assert hook is not None
    assert hook.hook_type == "before-feature"
    assert hook.step_text == "Given step"

    hook2 = parse_lifecycle_line("# @After-Scenario: Then step", 1)
    assert hook2 is not None
    assert hook2.hook_type == "after-scenario"


def test_parse_lifecycle_hooks_bom_file(tmp_path) -> None:
    feature_file = tmp_path / "test.feature"
    content = "# @before-all: Given setup\nFeature: Test\n"
    feature_file.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
    hooks = parse_lifecycle_hooks(str(feature_file))
    assert len(hooks) == 1
    assert hooks[0].hook_type == "before-all"


def test_execute_step_outside_feature_falls_through_to_registry(monkeypatch) -> None:
    """When execute_steps fails with 'outside of feature', fall through to registry."""
    called = {"registry": False}

    def impl(step_text: str) -> None:
        raise AssertionError("execute_steps() called outside of feature")

    def step_given_x(context: Any) -> None:
        called["registry"] = True

    _patch_registry(monkeypatch, FakeRegistry({"Given x": step_given_x}))
    context = FakeContextWithExecuteSteps(impl)
    _execute_step("Given x", context, hook_type="before-all")
    assert called["registry"] is True


def test_execute_step_outside_feature_falls_through_and_step_not_found(monkeypatch) -> None:
    """When execute_steps fails with 'outside of feature' and step not in registry, raise."""
    def impl(step_text: str) -> None:
        raise AssertionError("execute_steps() called outside of feature")

    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContextWithExecuteSteps(impl)
    with pytest.raises(LifecycleStepError) as exc_info:
        _execute_step("Given unknown", context, hook_type="after-all")
    assert "not found in registry" in exc_info.value.detail


def test_setup_lifecycle_hooks_empty_filename() -> None:
    context = FakeContext()
    feature = FakeFeature(filename="")
    setup_lifecycle_hooks(context, feature)
    assert not hasattr(context, "_lifecycle_hooks")


def test_parse_lifecycle_hooks_with_path_object(tmp_path) -> None:
    from pathlib import Path

    feature_file = tmp_path / "test.feature"
    feature_file.write_text("# @before-all: Given setup\nFeature: Test\n")
    hooks = parse_lifecycle_hooks(Path(feature_file))
    assert len(hooks) == 1
    assert hooks[0].hook_type == "before-all"


def test_parse_lifecycle_line_extra_spaces_around_colon() -> None:
    hook = parse_lifecycle_line("# @before-feature :  Given step", 1)
    assert hook is not None
    assert hook.hook_type == "before-feature"
    assert hook.step_text == "Given step"


def test_run_hooks_continue_on_error_three_hooks(monkeypatch) -> None:
    calls = []

    def step_ok(context: Any) -> None:
        calls.append("ok")

    def step_fail1(context: Any) -> None:
        calls.append("fail1")
        raise AssertionError("fail1")

    def step_fail2(context: Any) -> None:
        calls.append("fail2")
        raise ValueError("fail2")

    _patch_registry(
        monkeypatch,
        FakeRegistry({
            "Given ok": step_ok,
            "Given fail1": step_fail1,
            "Given fail2": step_fail2,
        }),
    )
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-scenario", step_text="Given ok", line=1),
        LifecycleHook(hook_type="before-scenario", step_text="Given fail1", line=2),
        LifecycleHook(hook_type="before-scenario", step_text="Given fail2", line=3),
    ]
    with pytest.raises(LifecycleStepError) as exc_info:
        run_before_scenario(context, FakeScenario(), continue_on_error=True)
    assert calls == ["ok", "fail1", "fail2"]
    assert "2 hook(s) failed" in exc_info.value.step_text
    assert "fail1" in exc_info.value.detail
    assert "fail2" in exc_info.value.detail


def test_parse_lifecycle_line_step_with_leading_spaces() -> None:
    hook = parse_lifecycle_line("# @after-scenario:    Then cleanup", 1)
    assert hook is not None
    assert hook.hook_type == "after-scenario"
    assert hook.step_text == "Then cleanup"


def test_run_hooks_no_matching_type(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    context._lifecycle_hooks = [
        LifecycleHook(hook_type="before-feature", step_text="Given x", line=1),
    ]
    run_before_scenario(context, FakeScenario())
    run_after_all(context)


def test_parse_lifecycle_hooks_no_hooks(tmp_path) -> None:
    feature_file = tmp_path / "test.feature"
    feature_file.write_text("Feature: Test\n  Scenario: S1\n    Given a step\n")
    hooks = parse_lifecycle_hooks(str(feature_file))
    assert hooks == []


def test_parse_lifecycle_line_mixed_case() -> None:
    hook = parse_lifecycle_line("# @BEFORE-FEATURE: Given setup", 1)
    assert hook is not None
    assert hook.hook_type == "before-feature"


def test_parse_lifecycle_line_after_all() -> None:
    hook = parse_lifecycle_line("# @after-all: Then cleanup", 1)
    assert hook is not None
    assert hook.hook_type == "after-all"
    assert hook.step_text == "Then cleanup"


def test_parse_lifecycle_line_before_step() -> None:
    hook = parse_lifecycle_line("# @before-step: Given init", 1)
    assert hook is not None
    assert hook.hook_type == "before-step"


def test_parse_lifecycle_line_after_step() -> None:
    hook = parse_lifecycle_line("# @after-step: Then verify", 1)
    assert hook is not None
    assert hook.hook_type == "after-step"


def test_parse_lifecycle_line_not_a_hook() -> None:
    hook = parse_lifecycle_line("# @jira TICKET-1", 1)
    assert hook is None


def test_parse_lifecycle_line_non_comment() -> None:
    hook = parse_lifecycle_line("Given a step", 1)
    assert hook is None


def test_run_hooks_all_types_no_hooks(monkeypatch) -> None:
    _patch_registry(monkeypatch, FakeRegistry({}))
    context = FakeContext()
    context._lifecycle_hooks = []
    run_before_feature(context, FakeFeature(filename="test.feature"))
    run_after_feature(context, FakeFeature(filename="test.feature"))
    run_before_scenario(context, FakeScenario())
    run_after_scenario(context, FakeScenario())
    run_before_step(context, FakeStep())
    run_after_step(context, FakeStep())
    run_before_all(context)
    run_after_all(context)
