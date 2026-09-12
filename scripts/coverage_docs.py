"""Render and verify README coverage metrics from coverage.py JSON output."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from opportunities.utils.files import atomic_write_text
from opportunities.utils.paths import find_project_root

# Resolve defaults from the checkout rather than the caller's working directory. Explicit
# paths remain available for tests and controlled tooling integrations.
_ROOT = find_project_root(Path(__file__))

# Keep coverage-owned content separate from the opportunity regions managed by
# opportunities.readme. Exact marker counts prevent a malformed README from being
# partially or ambiguously rewritten.
_BADGE_PATTERN = re.compile(
    r"<!-- BEGIN PYTHON COVERAGE BADGE -->\n.*?\n\s*<!-- END PYTHON COVERAGE BADGE -->",
    re.DOTALL,
)
_TABLE_PATTERN = re.compile(
    r"<!-- BEGIN PYTHON COVERAGE -->\n.*?\n<!-- END PYTHON COVERAGE -->",
    re.DOTALL,
)

# coverage.py uses platform-native separators in JSON file keys. Comparisons normalize
# them so the same report renderer works in local Windows runs and Linux CI.
_CLASSIFIER_PATH = "src/opportunities/pipeline/classification.py"


@dataclass(frozen=True, slots=True)
class CoverageMetrics:
    """Hold display-ready coverage values."""

    combined: str
    branches: str
    classifier_branches: str
    required: str
    passing: bool


def load_metrics(coverage_path: Path, pyproject_path: Path) -> CoverageMetrics:
    """Load coverage values and the enforced threshold from generated project data."""
    report = _mapping(_load_json(coverage_path), name="coverage report")
    totals = _mapping(report.get("totals"), name="coverage totals")
    files = _mapping(report.get("files"), name="coverage files")
    classifier = _classifier_summary(files)

    pyproject = _mapping(_load_toml(pyproject_path), name="pyproject")
    tool = _mapping(pyproject.get("tool"), name="pyproject tool section")
    coverage = _mapping(tool.get("coverage"), name="pyproject coverage section")
    settings = _mapping(coverage.get("report"), name="pyproject coverage report section")
    precision = _precision(settings.get("precision", 0))
    required = _percentage(settings.get("fail_under"), name="coverage fail_under")
    combined = _percentage(totals.get("percent_covered"), name="percent_covered")

    return CoverageMetrics(
        combined=_display_percentage(
            totals,
            numeric_key="percent_covered",
            display_key="percent_covered_display",
        ),
        branches=_display_percentage(
            totals,
            numeric_key="percent_branches_covered",
            display_key="percent_branches_covered_display",
        ),
        classifier_branches=_display_percentage(
            classifier,
            numeric_key="percent_branches_covered",
            display_key="percent_branches_covered_display",
        ),
        required=f"{required:.{precision}f}",
        passing=combined >= required,
    )


def render_coverage_docs(readme: str, metrics: CoverageMetrics) -> str:
    """Replace the two generated README coverage regions."""
    # A manually rendered below-threshold report must never receive a green badge.
    # The normal Make and CI paths stop at pytest's fail-under gate before this case.
    badge_color = "brightgreen" if metrics.passing else "red"
    badge = (
        "<!-- BEGIN PYTHON COVERAGE BADGE -->\n"
        '  <a href="#python-quality-baseline">\n'
        "    <img "
        f'src="https://img.shields.io/badge/critical_path_coverage-{metrics.combined}%25_'
        f'%7C_{metrics.branches}%25_branches-{badge_color}" '
        f'alt="Critical path coverage: {metrics.combined}%, including '
        f'{metrics.branches}% branch coverage" />\n'
        "  </a>\n"
        "  <!-- END PYTHON COVERAGE BADGE -->"
    )
    table = (
        "<!-- BEGIN PYTHON COVERAGE -->\n"
        "| Metric | Current | Required |\n"
        "|---|---:|---:|\n"
        f"| Combined statement and branch coverage | {metrics.combined}% | "
        f"≥ {metrics.required}% |\n"
        f"| Branch coverage | {metrics.branches}% | Reported |\n"
        f"| Classifier branch coverage | {metrics.classifier_branches}% | Reported |\n"
        "<!-- END PYTHON COVERAGE -->"
    )
    rendered = _replace_one(_BADGE_PATTERN, readme, badge, name="coverage badge")
    return _replace_one(_TABLE_PATTERN, rendered, table, name="coverage table")


def main(argv: Sequence[str] | None = None) -> int:
    """Render the README or verify that its generated coverage regions are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage", type=Path, default=_ROOT / "quality-reports" / "coverage.json"
    )
    parser.add_argument("--pyproject", type=Path, default=_ROOT / "pyproject.toml")
    parser.add_argument("--readme", type=Path, default=_ROOT / "README.md")
    parser.add_argument("--check", action="store_true", help="Fail instead of updating stale data")
    args = parser.parse_args(argv)

    try:
        metrics = load_metrics(args.coverage, args.pyproject)
        current = args.readme.read_text(encoding="utf-8")
        rendered = render_coverage_docs(current, metrics)
        if current == rendered:
            sys.stdout.write("README coverage metrics are current.\n")
            return 0
        if args.check:
            sys.stderr.write(
                "README coverage metrics are stale; run `make coverage` and commit README.md.\n"
            )
            return 1

        # Use the shared atomic writer so interruption cannot leave a truncated README.
        atomic_write_text(args.readme, rendered)
    except (OSError, UnicodeError, ValueError) as exc:
        sys.stderr.write(f"Coverage documentation error: {exc}\n")
        return 1

    sys.stdout.write("README coverage metrics updated.\n")
    return 0


def _load_json(path: Path) -> object:
    try:
        return cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read coverage JSON: {path}") from exc


def _load_toml(path: Path) -> object:
    try:
        return cast(object, tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"could not read project configuration: {path}") from exc


def _mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _percentage(value: object, *, name: str) -> float:
    number = _number(value, name=name)
    if not 0 <= number <= 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return number


def _precision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
        raise ValueError("coverage precision must be an integer from 0 through 4")
    return value


def _display_percentage(
    summary: Mapping[str, object], *, numeric_key: str, display_key: str
) -> str:
    numeric = _percentage(summary.get(numeric_key), name=numeric_key)
    display = summary.get(display_key)
    if not isinstance(display, str) or not re.fullmatch(r"\d+(?:\.\d+)?", display):
        raise ValueError(f"{display_key} must be a numeric display string")

    # Reject internally inconsistent reports instead of publishing a display field that
    # does not represent its numeric coverage.py value at the reported precision.
    decimals = len(display.partition(".")[2])
    tolerance = 0.5 * 10**-decimals + 1e-9
    if not 0 <= float(display) <= 100 or abs(float(display) - numeric) > tolerance:
        raise ValueError(f"{display_key} does not match {numeric_key}")
    return display


def _classifier_summary(files: Mapping[str, object]) -> Mapping[str, object]:
    for path, value in files.items():
        normalized = path.replace("\\", "/").removeprefix("./")
        if normalized == _CLASSIFIER_PATH:
            file_report = _mapping(value, name="classifier coverage")
            return _mapping(file_report.get("summary"), name="classifier coverage summary")
    raise ValueError(f"coverage report does not contain {_CLASSIFIER_PATH}")


def _replace_one(pattern: re.Pattern[str], content: str, replacement: str, *, name: str) -> str:
    matches = pattern.findall(content)
    if len(matches) != 1:
        raise ValueError(f"README must contain exactly one generated {name} region")
    return pattern.sub(lambda _match: replacement, content, count=1)


if __name__ == "__main__":
    raise SystemExit(main())
