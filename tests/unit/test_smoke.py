"""Smoke tests: verify all public API is importable and callable."""

from __future__ import annotations

import behave_comments


def test_version() -> None:
    assert behave_comments.__version__ == "1.0.0"


def test_all_exports_importable() -> None:
    for name in behave_comments.__all__:
        assert hasattr(behave_comments, name), f"Missing export: {name}"


def test_all_exports_count() -> None:
    assert len(behave_comments.__all__) == 26


def test_errors_hierarchy() -> None:
    assert issubclass(behave_comments.ContentTypeError, behave_comments.BehaveCommentsError)
    assert issubclass(behave_comments.ParseError, behave_comments.BehaveCommentsError)
    assert issubclass(behave_comments.AnnotationParseError, behave_comments.BehaveCommentsError)
    assert issubclass(behave_comments.LifecycleStepError, behave_comments.BehaveCommentsError)


def test_models_are_dataclasses() -> None:
    from dataclasses import is_dataclass

    assert is_dataclass(behave_comments.TextBlock)
    assert is_dataclass(behave_comments.Annotation)
    assert is_dataclass(behave_comments.LifecycleHook)


def test_supported_content_types_is_frozenset() -> None:
    assert isinstance(behave_comments.SUPPORTED_CONTENT_TYPES, frozenset)


def test_functions_are_callable() -> None:
    callables = [
        behave_comments.detect_content_type,
        behave_comments.parse_text,
        behave_comments.extract_text_block,
        behave_comments.with_parsed_text,
        behave_comments.extract_annotations,
        behave_comments.annotations_to_tags,
        behave_comments.inject_metadata,
        behave_comments.setup_lifecycle_hooks,
        behave_comments.run_before_feature,
        behave_comments.run_after_feature,
        behave_comments.run_before_scenario,
        behave_comments.run_after_scenario,
        behave_comments.run_before_step,
        behave_comments.run_after_step,
        behave_comments.run_before_all,
        behave_comments.run_after_all,
        behave_comments.setup_lifecycle_hooks_from_path,
    ]
    for func in callables:
        assert callable(func), f"Not callable: {func.__name__}"
