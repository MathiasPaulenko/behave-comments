# behave-comments

Parse doc strings, extract metadata from comments, and declare lifecycle hooks in Behave `.feature` files.

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
from behave_comments import with_parsed_text

@given("a JSON document")
@with_parsed_text()
def step_given_json(context, text_block):
    data = text_block.parsed  # {"name": "Alice", "age": 30}
```

Supported content types: `json`, `yaml`, `xml`, `csv`, `form-urlencoded`, `graphql`, `text/plain`.

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

# Optional: YAML support
pip install behave-comments[yaml]
```

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
    text_block = extract_text_block(context.step)
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
    run_before_feature,
    run_after_feature,
    run_before_scenario,
    run_after_scenario,
    run_before_step,
    run_after_step,
)

def before_feature(context, feature):
    setup_lifecycle_hooks(context, feature)
    run_before_feature(context, feature)

def after_feature(context, feature):
    run_after_feature(context, feature)

def before_scenario(context, scenario):
    run_before_scenario(context, scenario)

def after_scenario(context, scenario):
    run_after_scenario(context, scenario)
```

## API Reference

### Errors

- `BehaveCommentsError` — Base exception
- `ContentTypeError` — Unsupported content type
- `ParseError` — Parsing failed
- `MissingDependencyError` — Optional dependency missing (e.g. pyyaml)
- `AnnotationParseError` — Invalid annotation syntax
- `LifecycleStepError` — Lifecycle step execution failed

### Models

- `TextBlock(content, content_type, line, parsed)` — Parsed doc string
- `Annotation(key, value, line, scope, scope_name)` — Extracted annotation
- `LifecycleHook(hook_type, step_text, line)` — Lifecycle hook declaration

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check behave_comments/
mypy behave_comments/
```

## License

MIT
