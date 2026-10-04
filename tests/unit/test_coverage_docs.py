from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "docs" / "coverage_docs.py"


@pytest.fixture
def generated_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Use a custom README target to test --document independently of the default guide."""
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
                    # Windows-style report keys must resolve on POSIX too.
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


def test_renders_table_and_then_passes_check(
    generated_inputs: tuple[Path, Path, Path],
) -> None:
    coverage_path, pyproject_path, readme_path = generated_inputs

    # Check mode must report stale metrics without repairing the document it validates.
    stale = _run_script(coverage_path, pyproject_path, readme_path, "--check")
    assert stale.returncode == 1
    assert "Coverage metrics are stale" in stale.stderr
    assert readme_path.read_text(encoding="utf-8") == _readme_template()

    rendered = _run_script(coverage_path, pyproject_path, readme_path)
    checked = _run_script(coverage_path, pyproject_path, readme_path, "--check")
    content = readme_path.read_text(encoding="utf-8")

    assert rendered.returncode == 0, rendered.stderr
    assert checked.returncode == 0, checked.stderr
    assert "actions/workflows/codeql.yml/badge.svg" in content
    assert "| Combined statement and branch coverage | 90.1% | ≥ 85.0% |" in content
    assert "| Classifier branch coverage | 97.5% | Reported |" in content


def test_default_document_targets_nested_guide_independently_of_working_directory(
    generated_inputs: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.docs import coverage_docs

    coverage_path, pyproject_path, readme_path = generated_inputs
    root = pyproject_path.parent
    document = root / "docs/maintainers/engineering/testing.md"
    document.parent.mkdir(parents=True)
    document.write_text(_readme_template(), encoding="utf-8")
    monkeypatch.setattr(coverage_docs, "_ROOT", root)
    monkeypatch.chdir(root.parent)
    args = ["--coverage", str(coverage_path)]

    assert coverage_docs.main([*args, "--check"]) == 1
    assert document.read_text(encoding="utf-8") == _readme_template()
    assert coverage_docs.main(args) == 0
    assert coverage_docs.main([*args, "--check"]) == 0
    assert "| Classifier branch coverage | 97.5% | Reported |" in document.read_text(
        encoding="utf-8"
    )
    assert readme_path.read_text(encoding="utf-8") == _readme_template()
    assert not (root / "docs/maintainers/testing.md").exists()


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
            "--document",
            str(readme_path),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _readme_template() -> str:
    return """# README

<img src="https://github.com/example/project/actions/workflows/codeql.yml/badge.svg" />

<!-- BEGIN PYTHON COVERAGE -->
old table
<!-- END PYTHON COVERAGE -->
"""
