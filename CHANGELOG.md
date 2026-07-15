# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-07-15

### Added

- Project scaffolding: `pyproject.toml` with hatchling build backend, extras `[yaml]`, `[dev]`.
- Tooling configuration: ruff (`E,F,W,I,UP,B,SIM,C4`, line-length 100), mypy (`--strict`), pytest with coverage threshold 90%.
- Text block parsing with content type detection: `json`, `yaml`, `xml`, `csv`, `form-urlencoded`, `graphql`, `text/plain`.
- `with_parsed_text` decorator and `extract_text_block` function for doc string parsing.
- Metadata annotations from `# @key value` comments with feature and scenario scope.
- `inject_metadata`, `extract_annotations`, `annotations_to_tags` functions.
- Lifecycle hooks declared in comments: `before-feature`, `before-scenario`, `before-step`, `before-all`, `after-feature`, `after-scenario`, `after-step`, `after-all`.
- `setup_lifecycle_hooks` and `run_*` functions for hook execution.
- Error hierarchy: `BehaveCommentsError`, `ContentTypeError`, `ParseError`, `MissingDependencyError`, `AnnotationParseError`, `LifecycleStepError`.
- Frozen dataclass models: `TextBlock`, `Annotation`, `LifecycleHook`.
- 288 tests (unit, integration, E2E) with 96% coverage.
- MIT license.
