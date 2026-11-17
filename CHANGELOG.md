# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-11-17

### Fixed

- Enforce an explicit, platform-independent nesting depth limit (100
  levels) for JSON and YAML doc strings. Python 3.14 measures C-level
  recursion in stack bytes rather than frames, so a deeply nested input
  raised ``RecursionError`` on some platforms but parsed successfully on
  others. The depth of parsed structures is now validated iteratively.

## [1.1.1] - 2026-11-17

### Fixed

- `run_before_step`/`run_after_step` no longer recurse forever: Behave fires
  `before_step`/`after_step` hooks for `context.execute_steps()` substeps, so a
  `# @before-step`/`# @after-step` hook executing through `execute_steps`
  re-entered itself. Nested step-hook execution is now skipped while a
  lifecycle step runs.
- `parse_text` rejects non-string `text` and `content_type` arguments with
  `TypeError` instead of leaking `AttributeError` or silently returning a
  non-str "parsed" value for `text/plain`.
- `json`/`yaml` parsing of pathologically nested input raises `ParseError`
  instead of a raw `RecursionError`.
- `_declared_content_type` no longer crashes on negative/float `text.line`
  values or non-UTF-8 feature files, and reads only up to the doc string line
  instead of the whole file.
- `extract_text_block` reports `TextBlock.line` as the doc string opening line
  (`text.line`) when available, and rejects non-string `text` values.
- `setup_lifecycle_hooks` and `inject_metadata` reset their context state when
  the feature filename is missing, so hooks/metadata from a previous call on
  the same context cannot leak in.
- `inject_metadata` and `with_parsed_text` validate `prefix`/`param_name` as
  Python identifiers (`ValueError`).
- Lifecycle steps starting with `And`, `But`, or `*` now resolve through the
  registry fallback (previously rejected with "must start with ...").
- `# language: ES` (uppercase code) resolves the localized keyword map.
- `__version__` fallback matches the released version (was "1.0.0").
- `SECURITY.md` supported-versions table updated for 1.1.x.

### Changed

- `SUPPORTED_CONTENT_TYPES` is derived from the parser map (single source).

## [1.1.0] - 2026-10-02

### Fixed

- `extract_text_block` now recovers the media type declared on the doc string
  opening line (`"""json`), which Behave discards: it is read back from the
  feature file via `text.line` + `feature.filename`. Previously the documented
  `"""json` syntax silently produced `text/plain` with unparsed content.
- `with_parsed_text` no longer swallows the first positional step parameter
  (e.g. `(\d+)` groups or anonymous parse fields). A positional argument is only
  treated as the step object when it has a `text` attribute.
- `extract_annotations` and `parse_lifecycle_hooks` now skip doc string bodies:
  `# @key value` comments or Gherkin-looking lines inside `"""`/`'''` blocks no
  longer produce false annotations, hooks, or scope changes.
- `setup_lifecycle_hooks_from_path` accepts a directory (as the README shows):
  hooks are collected from every `*.feature` file inside it, recursively.
- `before-all`/`after-all` hooks are now accumulated in a separate global store,
  so `run_after_all` no longer loses hooks declared in earlier features when
  `setup_lifecycle_hooks` overwrites the per-feature store.
- `_parse_csv` drops DictReader restkey overflow values keyed by `None`.
- `inject_metadata` stores `line` as `int` (was `str`), matching `Annotation.line`.
- Removed the `behave.runner` registry fallback — that attribute never existed;
  `behave.step_registry.registry` is the import path on both 1.2.6 and 1.3.x.

### Added

- `extract_annotations` supports localized feature files via `# language: xx`
  (keywords resolved through `behave.i18n`), plus the `Example:` and
  `Scenarios:` Gherkin aliases.
- `LifecycleHook` gained a `filename` field (defaults to `""`).
- `parse_annotation_line` and `parse_lifecycle_hooks` are exported in the public API.
- Python 3.14 classifier and CI matrix entry; verified against behave 1.3.3.
- E2E steps now assert parsed content; regression tests for the fixes above.

### Changed

- Dropped the incorrect `Framework :: Pytest` trove classifier.
- `behave` dependency bounded to `>=1.2.6,<2`.
- `__version__` now comes from installed package metadata (single source of
  truth in `pyproject.toml`), with a static fallback.
- Dev tooling floors bumped (ruff>=0.14, mypy>=1.18, pytest-cov>=6.0); CI
  actions updated to checkout@v7, setup-python@v7, upload/download-artifact@v6;
  pre-commit hooks bumped (ruff v0.16.9, mypy v2.3.1, hooks v6.0.0).

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
