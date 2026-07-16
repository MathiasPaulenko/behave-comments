"""behave-comments: parse doc strings, metadata, and lifecycle hooks."""

from __future__ import annotations

import logging

from behave_comments.annotations import (
    annotations_to_tags,
    extract_annotations,
    inject_metadata,
)
from behave_comments.decorators import with_parsed_text
from behave_comments.errors import (
    AnnotationParseError,
    BehaveCommentsError,
    ContentTypeError,
    LifecycleStepError,
    ParseError,
)
from behave_comments.lifecycle import (
    LifecycleHook,
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
from behave_comments.models import Annotation, TextBlock
from behave_comments.parser import (
    SUPPORTED_CONTENT_TYPES,
    detect_content_type,
    extract_text_block,
    parse_text,
)

__version__ = "1.0.0"

__all__ = [
    "Annotation",
    "AnnotationParseError",
    "BehaveCommentsError",
    "ContentTypeError",
    "LifecycleHook",
    "LifecycleStepError",
    "ParseError",
    "SUPPORTED_CONTENT_TYPES",
    "TextBlock",
    "annotations_to_tags",
    "detect_content_type",
    "extract_annotations",
    "extract_text_block",
    "inject_metadata",
    "parse_text",
    "run_after_all",
    "run_after_feature",
    "run_after_scenario",
    "run_after_step",
    "run_before_all",
    "run_before_feature",
    "run_before_scenario",
    "run_before_step",
    "setup_lifecycle_hooks",
    "setup_lifecycle_hooks_from_path",
    "with_parsed_text",
]

logging.getLogger(__name__).addHandler(logging.NullHandler())
