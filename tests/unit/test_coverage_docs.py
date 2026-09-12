from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "coverage_docs.py"


@pytest.fixture
def generated_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    coverage_path = tmp_path / "coverage.json"
    pyproject_path = tmp_path / "pyproject.toml"
    readme_path = tmp_path / "README.md"
    coverage_path.write_text(
        json.dumps(
            {
                "totals": {
                    "percent_covered": 90.12,
                    "percent_covered_display": "90.1",
                    "percent_branches_covered": 82.73,
                    "percent_branches_covered_display": "82.7",
                },
                "files": {
                    "src\\opportunities\\pipeline\\classification.py": {
                        "summary": {
                            "percent_branches_covered": 97.5,
                            "percent_branches_covered_display": "97.5",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    pyproject_path.write_text(
        "[tool.coverage.report]\nfail_under = 85\nprecision = 1\n",
        encoding="utf-8",
    )
    readme_path.write_text(_readme_template(), encoding="utf-8")
    return coverage_path, pyproject_path, readme_path


def test_renders_badge_and_table_and_then_passes_check(
    generated_inputs: tuple[Path, Path, Path],
) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs

    rendered = _run_script(coverage_path, pyproject_path, readme_path)
    checked = _run_script(coverage_path, pyproject_path, readme_path, "--check")
    content = readme_path.read_text(encoding="utf-8")

    assert rendered.returncode == 0, rendered.stderr
    assert checked.returncode == 0, checked.stderr
    assert "critical_path_coverage-90.1%25_%7C_82.7%25_branches-brightgreen" in content
    assert "| Combined statement and branch coverage | 90.1% | ≥ 85.0% |" in content
    assert "| Classifier branch coverage | 97.5% | Reported |" in content


def test_check_rejects_stale_metrics(generated_inputs: tuple[Path, Path, Path]) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs

    result = _run_script(coverage_path, pyproject_path, readme_path, "--check")

    assert result.returncode == 1
    assert "README coverage metrics are stale" in result.stderr
    assert readme_path.read_text(encoding="utf-8") == _readme_template()


def test_below_threshold_report_uses_red_badge(
    generated_inputs: tuple[Path, Path, Path],
) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs
    report = json.loads(coverage_path.read_text(encoding="utf-8"))
    report["totals"]["percent_covered"] = 84.94
    report["totals"]["percent_covered_display"] = "84.9"
    coverage_path.write_text(json.dumps(report), encoding="utf-8")

    result = _run_script(coverage_path, pyproject_path, readme_path)

    assert result.returncode == 0, result.stderr
    assert "84.9%25_%7C_82.7%25_branches-red" in readme_path.read_text(encoding="utf-8")


def test_invalid_report_fails_cleanly_without_rewriting_readme(
    generated_inputs: tuple[Path, Path, Path],
) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs
    original = readme_path.read_text(encoding="utf-8")
    coverage_path.write_text("{}", encoding="utf-8")

    result = _run_script(coverage_path, pyproject_path, readme_path)

    assert result.returncode == 1
    assert result.stderr.startswith("Coverage documentation error:")
    assert "Traceback" not in result.stderr
    assert readme_path.read_text(encoding="utf-8") == original


def test_rejects_duplicate_generated_regions(
    generated_inputs: tuple[Path, Path, Path],
) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs
    readme_path.write_text(
        _readme_template().replace(
            "<!-- END PYTHON COVERAGE -->",
            "<!-- END PYTHON COVERAGE -->\n<!-- BEGIN PYTHON COVERAGE -->\nold\n"
            "<!-- END PYTHON COVERAGE -->",
        ),
        encoding="utf-8",
    )

    result = _run_script(coverage_path, pyproject_path, readme_path)

    assert result.returncode != 0
    assert "exactly one generated coverage table region" in result.stderr


def _run_script(
    coverage_path: Path,
    pyproject_path: Path,
    readme_path: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--coverage",
            str(coverage_path),
            "--pyproject",
            str(pyproject_path),
            "--readme",
            str(readme_path),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _readme_template() -> str:
    return """# README

<!-- BEGIN PYTHON COVERAGE BADGE -->
old badge
<!-- END PYTHON COVERAGE BADGE -->

<!-- BEGIN PYTHON COVERAGE -->
old table
<!-- END PYTHON COVERAGE -->
"""
