"""End-to-end tests: run Behave against static feature files."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = Path(__file__).parent / "features"


def run_behave_e2e(feature_name: str) -> subprocess.CompletedProcess:
    """Run Behave against a specific E2E feature file."""
    env = {**os.environ}
    pythonpath = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = pythonpath
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "behave",
            "--no-color",
            "--format=plain",
            str(FEATURES_DIR / feature_name),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=Path(__file__).parent,
        env=env,
    )


def test_text_blocks_e2e():
    result = run_behave_e2e("text_blocks.feature")
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_annotations_e2e():
    result = run_behave_e2e("annotations.feature")
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_lifecycle_e2e():
    result = run_behave_e2e("lifecycle.feature")
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_edge_cases_e2e():
    result = run_behave_e2e("edge_cases.feature")
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
