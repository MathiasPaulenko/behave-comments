.PHONY: install dev test lint typecheck format clean build

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	ruff check behave_comments/ tests/
	ruff format --check behave_comments/ tests/

typecheck:
	mypy behave_comments/

format:
	ruff check --fix behave_comments/ tests/
	ruff format behave_comments/ tests/

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	python -m build
