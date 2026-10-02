# behave-comments

[![PyPI version](https://img.shields.io/pypi/v/behave-comments)](https://pypi.org/project/behave-comments/)
[![Python versions](https://img.shields.io/pypi/pyversions/behave-comments)](https://pypi.org/project/behave-comments/)
[![CI](https://github.com/MathiasPaulenko/behave-comments/actions/workflows/ci.yml/badge.svg)](https://github.com/MathiasPaulenko/behave-comments/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/MathiasPaulenko/behave-comments)](LICENSE)

Parse doc strings, extract metadata from comments, and declare lifecycle hooks in Behave `.feature` files.

Requires Python 3.11+ and behave 1.2.6–1.3.x.

## Features

### Text Block Parsing

Detect content types in doc strings and parse them automatically:

```gherkin
Given a JSON document
  """json
  {"name": "Alice", "age": 30}
  """
```

```python
from behave import given
from behave_comments import with_parsed_text

@given("a JSON document")
@with_parsed_text()
def step_given_json(context, text_block):
    data = text_block.parsed  # {"name": "Alice", "age": 30}
```

Supported content types: `json`, `yaml`, `xml`, `csv`, `form-urlencoded`, `graphql`, `text/plain`.

The content type can be declared on the doc string opening line (`"""json`)
or as the first line inside the doc string body — both are detected, since
Behave itself discards the opening-line media type.

### Metadata Annotations

Extract structured metadata from `# @key value` comments:

```gherkin
# @jira TICKET-42
# @owner team-alpha
Feature: Login

  # @id SC-001
  Scenario: Successful login
    Given the user is on the login page
```

Annotations attach to the Gherkin element that follows them (`feature`,
`scenario`, `background`, `rule`, `examples`, or `step` scope). Comments inside
doc strings are ignored, and localized feature files (`# language: xx`) are
supported.

```python
from behave_comments import inject_metadata

def before_feature(context, feature):
    inject_metadata(context, feature)
    # context.metadata == {
    #   "feature": [{"key": "jira", "value": "TICKET-42"}, ...],
    #   "scenario": [{"key": "id", "value": "SC-001"}, ...],
    # }
```

### Lifecycle Hooks

Declare setup/teardown steps directly in comments:

```gherkin
# @before-feature: Given a clean database
Feature: User Tests

  # @after-scenario: Then clear the cache
  Scenario: User login
    Given a registered user
```

```python
from behave_comments import setup_lifecycle_hooks, run_before_feature, run_after_scenario

def before_feature(context, feature):
    setup_lifecycle_hooks(context, feature)
    run_before_feature(context, feature)

def after_scenario(context, scenario):
    run_after_scenario(context, scenario)
```

## Installation

```bash
pip install behave-comments
```

YAML support is included — `pyyaml` is a required dependency.

## Usage

### Text Blocks

```python
from behave_comments import with_parsed_text, extract_text_block

# Option 1: Decorator
@given("a JSON document")
@with_parsed_text()
def step(context, text_block):
    data = text_block.parsed

# Option 2: Manual extraction
def step(context):
    text_block = extract_text_block(context)  # context.text holds the doc string
    data = text_block.parsed
```

### Annotations

```python
from behave_comments import inject_metadata, extract_annotations, annotations_to_tags

def before_feature(context, feature):
    inject_metadata(context, feature)

# Or extract directly
annotations = extract_annotations("features/login.feature")
tags = annotations_to_tags(annotations)
```

### Lifecycle Hooks Usage

```python
from behave_comments import (
    setup_lifecycle_hooks,
    setup_lifecycle_hooks_from_path,
    run_before_all,
    run_after_all,
    run_before_feature,
    run_after_feature,
    run_before_scenario,
    run_after_scenario,
    run_before_step,
    run_after_step,
)

def before_all(context):
    # Accepts a single .feature file or a directory (hooks are collected
    # from every *.feature file inside it, recursively).
    setup_lifecycle_hooks_from_path(context, "features/")
    run_before_all(context)

def after_all(context):
    run_after_all(context)

def before_feature(context, feature):
    setup_lifecycle_hooks(context, feature)
    run_before_feature(context, feature)

def after_feature(context, feature):
    run_after_feature(context, feature)

def before_scenario(context, scenario):
    run_before_scenario(context, scenario)

def after_scenario(context, scenario):
    run_after_scenario(context, scenario)

def before_step(context, step):
    run_before_step(context, step)

def after_step(context, step):
    run_after_step(context, step)
```

## API Reference

### Functions

- `extract_text_block(source)` — Extract and parse a step's doc string (accepts a step object or `context`)
- `parse_text(text, content_type)` — Parse a text block by content type
- `detect_content_type(opening_line)` — Detect the content type from a doc string opening line
- `with_parsed_text(param_name)` — Decorator injecting a `TextBlock` into a step
- `extract_annotations(feature_path)` — Extract annotations from a .feature file
- `parse_annotation_line(line, line_number)` — Parse a single comment line as an annotation
- `annotations_to_tags(annotations, dedup=False)` — Convert annotations to `@key-value` tag strings
- `inject_metadata(context, feature, prefix="metadata")` — Inject annotations into `context`
- `parse_lifecycle_line(line, line_number)` — Parse a single comment line as a hook declaration
- `parse_lifecycle_hooks(feature_path)` — Extract all hook declarations from a .feature file
- `setup_lifecycle_hooks(context, feature)` / `setup_lifecycle_hooks_from_path(context, path)` — Load hooks into context
- `run_before_all/after_all/before_feature/after_feature/before_scenario/after_scenario/before_step/after_step` — Execute stored hooks

### Errors

- `BehaveCommentsError` — Base exception
- `ContentTypeError` — Unsupported content type
- `ParseError` — Parsing failed
- `AnnotationParseError` — Invalid annotation syntax
- `LifecycleStepError` — Lifecycle step execution failed

### Models

- `TextBlock(content, content_type, line, parsed)` — Parsed doc string
- `Annotation(key, value, line, scope, scope_name)` — Extracted annotation
- `LifecycleHook(hook_type, step_text, line, filename)` — Lifecycle hook declaration

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check behave_comments tests
mypy behave_comments/
```

## License

MIT
