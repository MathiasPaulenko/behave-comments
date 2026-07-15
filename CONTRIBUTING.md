# Contributing to behave-comments

Thank you for your interest in contributing! This document covers the basics.

## Development Setup

```bash
git clone https://github.com/MathiasPaulenko/behave-comments.git
cd behave-comments
pip install -e ".[dev]"
```

## Workflow

1. Fork the repository and create a feature branch.
2. Write tests for your changes.
3. Ensure all checks pass:

```bash
ruff check behave_comments/ tests/
mypy behave_comments/
pytest --cov=behave_comments
```

4. Commit with clear, descriptive messages.
5. Open a pull request referencing any related issues.

## Code Style

- Python 3.11+ with type hints on all public functions.
- Line length: 100 characters.
- Ruff for linting and formatting.
- mypy --strict for type checking.

## Testing

- **Unit tests**: `tests/unit/` — fast, isolated, no external dependencies.
- **Integration tests**: `tests/integration/` — run Behave as subprocess.
- **E2E tests**: `tests/e2e/` — static feature files with real Behave runs.

Coverage must stay at or above 90%.

## Pull Requests

- Keep PRs focused and small.
- Include tests for new features.
- Update documentation (README, docstrings) as needed.
- Follow the PR template.

## Reporting Issues

Use the issue templates provided. Include:

- Python version and OS.
- Minimal reproduction steps.
- Expected vs actual behavior.
- Relevant logs or error messages.

## License

By contributing, you agree that your contributions are licensed under the MIT
License.
