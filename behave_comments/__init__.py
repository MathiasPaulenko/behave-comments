"""behave-comments: parse doc strings, metadata, and lifecycle hooks."""

from __future__ import annotations

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
    MissingDependencyError,
    ParseError,
)
from behave_comments.lifecycle import (
    LifecycleHook,
    run_after_feature,
    run_after_scenario,
    run_after_step,
    run_before_feature,
    run_before_scenario,
    run_before_step,
    setup_lifecycle_hooks,
)
from behave_comments.models import Annotation, TextBlock
from behave_comments.parser import (
    SUPPORTED_CONTENT_TYPES,
    detect_content_type,
    extract_text_block,
    parse_text,
)

__version__ = "0.1.0"

__all__ = [
    "Annotation",
    "AnnotationParseError",
    "BehaveCommentsError",
    "ContentTypeError",
    "LifecycleHook",
    "LifecycleStepError",
    "MissingDependencyError",
    "ParseError",
    "SUPPORTED_CONTENT_TYPES",
    "TextBlock",
    "annotations_to_tags",
    "detect_content_type",
    "extract_annotations",
    "extract_text_block",
    "inject_metadata",
    "parse_text",
    "run_after_feature",
    "run_after_scenario",
    "run_after_step",
    "run_before_feature",
    "run_before_scenario",
    "run_before_step",
    "setup_lifecycle_hooks",
    "with_parsed_text",
]

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
