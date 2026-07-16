# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-07-16

### Changed

- Removed `MissingDependencyError` (pyyaml is now a required dependency, the error was never raised).
- `inject_metadata` and `setup_lifecycle_hooks` now treat empty-string filenames the same as `None`.
- `parse_lifecycle_hooks` and `setup_lifecycle_hooks_from_path` accept `str | Path` for consistency.
- `extract_annotations` now detects `Scenario Template:` (Gherkin 6 alias for `Scenario Outline:`).
- `extract_annotations` now detects Gherkin keywords without space after colon (e.g. `Feature:Name`).
- Development status updated to Production/Stable.

### Added

- 589 tests (unit, integration, E2E) with 100% coverage.

## [0.1.0] - 2025-07-15

### Added

- Project scaffolding: `pyproject.toml` with hatchling build backend, extras `[dev]`.
- Tooling configuration: ruff (`E,F,W,I,UP,B,SIM,C4`, line-length 100), mypy (`--strict`), pytest with coverage threshold 90%.
- Text block parsing with content type detection: `json`, `yaml`, `xml`, `csv`, `form-urlencoded`, `graphql`, `text/plain`.
- `with_parsed_text` decorator and `extract_text_block` function for doc string parsing.
- Metadata annotations from `# @key value` comments with feature and scenario scope.
- `inject_metadata`, `extract_annotations`, `annotations_to_tags` functions.
- Lifecycle hooks declared in comments: `before-feature`, `before-scenario`, `before-step`, `before-all`, `after-feature`, `after-scenario`, `after-step`, `after-all`.
- `setup_lifecycle_hooks` and `run_*` functions for hook execution.
- Error hierarchy: `BehaveCommentsError`, `ContentTypeError`, `ParseError`, `AnnotationParseError`, `LifecycleStepError`.
- Frozen dataclass models: `TextBlock`, `Annotation`, `LifecycleHook`.
- MIT license.
