"""Infrastructure for integration tests: run Behave as subprocess."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest


@dataclass
class BehaveResult:
    """Result of a Behave subprocess run.

    Attributes:
        returncode: Exit code (0 = success).
        stdout: Standard output.
        stderr: Standard error.
    """

    returncode: int
    stdout: str
    stderr: str


@pytest.fixture
def run_behave(tmp_path: Path) -> Callable[..., BehaveResult]:
    """Fixture to run Behave against a temporary feature directory.

    Returns a function that creates feature files, steps, and environment.py
    in a temp directory, then runs ``behave`` as a subprocess.
    """

    def _run(
        feature_content: str,
        *,
        steps_content: str = "",
        environment_content: str = "",
        feature_filename: str = "test.feature",
    ) -> BehaveResult:
        features_dir = tmp_path / "features"
        steps_dir = features_dir / "steps"
        features_dir.mkdir(parents=True, exist_ok=True)
        steps_dir.mkdir(parents=True, exist_ok=True)

        (features_dir / feature_filename).write_text(
            dedent(feature_content), encoding="utf-8"
        )

        if steps_content:
            (steps_dir / "steps.py").write_text(
                dedent(steps_content), encoding="utf-8"
            )

        if environment_content:
            (features_dir / "environment.py").write_text(
                dedent(environment_content), encoding="utf-8"
            )

        result = subprocess.run(
            [sys.executable, "-m", "behave", "--no-color", "--format=plain", str(features_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        return BehaveResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return _run
