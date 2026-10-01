"""Offline regression tests for the canonical-state README review boundary."""

from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from opportunities.readme import (
    BEGIN_MARKER,
    END_MARKER,
    STATE_SEAL_PREFIX,
    SUMMARY_BEGIN_MARKER,
    SUMMARY_END_MARKER,
    ReadmeMetadata,
    render_readme,
)
from tests.shell_helpers import offline_shell_environment

WORKFLOWS = Path(__file__).parents[2] / ".github" / "workflows"


def workflow(name: str) -> dict[str, object]:
    # BaseLoader preserves GitHub's "on" key and scalar strings without YAML 1.1 coercion.
    document: dict[str, object] = yaml.load(
        (WORKFLOWS / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    return document


def process_steps() -> list[dict[str, object]]:
    document = yaml.load(
        (WORKFLOWS / "reusable-process-state.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    steps: list[dict[str, object]] = document["jobs"]["process"]["steps"]
    return steps


def process_step(name: str) -> dict[str, object]:
    return next(step for step in process_steps() if step.get("name") == name)


def projection(tmp_path: Path, timestamp: datetime) -> str:
    readme = tmp_path / "synthetic-README.md"
    readme.write_text(
        f"# Synthetic directory\n{SUMMARY_BEGIN_MARKER}\n{SUMMARY_END_MARKER}\n"
        f"{BEGIN_MARKER}\n{END_MARKER}\n",
        encoding="utf-8",
        newline="\n",
    )
    render_readme(readme, [], ReadmeMetadata(0, timestamp))
    return readme.read_text(encoding="utf-8")


def run_review_gate(
    tmp_path: Path,
    reviewed: str,
    rendered: str,
    *,
    adopt: bool = False,
    recover: bool = False,
    render_status: int = 0,
) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("README workflow tests require Bash")
    (tmp_path / "README.md").write_text(reviewed, encoding="utf-8", newline="\n")
    (tmp_path / "rendered.md").write_text(rendered, encoding="utf-8", newline="\n")
    script = process_step("Require restored state to match reviewed main")["run"]
    assert isinstance(script, str)
    # Only the render command is replaced; execute the checked-in comparison and exits.
    fake_render = """
uv() {
  if [ "$*" != "run opportunities render" ]; then return 98; fi
  if [ "$RENDER_STATUS" != "0" ]; then return "$RENDER_STATUS"; fi
  cp rendered.md README.md
}
"""
    result = subprocess.run(
        [bash, "-c", fake_render + script],
        cwd=tmp_path,
        env={
            **offline_shell_environment(tmp_path),
            "RUNNER_TEMP": tmp_path.as_posix(),
            "ADOPT_PUBLIC_REVIEW_SEAL": str(adopt).lower(),
            "RECOVER_README_PROPOSAL": str(recover).lower(),
            "RENDER_STATUS": str(render_status),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert not (tmp_path / "blocked-network.log").exists(), result.stderr
    return result


@pytest.mark.parametrize(("adopt", "recover"), [(False, False), (True, False), (False, True)])
def test_matching_reviewed_state_passes(tmp_path: Path, adopt: bool, recover: bool) -> None:
    reviewed = projection(tmp_path, datetime(2026, 9, 28, tzinfo=UTC))
    result = run_review_gate(tmp_path, reviewed, reviewed, adopt=adopt, recover=recover)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(("adopt", "recover"), [(False, False), (True, False), (False, True)])
def test_only_explicit_recovery_can_propose_unmerged_state(
    tmp_path: Path, adopt: bool, recover: bool
) -> None:
    timestamp = datetime(2026, 9, 28, tzinfo=UTC)
    reviewed = projection(tmp_path, timestamp)
    # Even a seal-only mismatch must block new collection and deployment.
    restored = projection(tmp_path, timestamp + timedelta(microseconds=1))
    assert reviewed != restored
    result = run_review_gate(tmp_path, reviewed, restored, adopt=adopt, recover=recover)
    if recover:
        assert result.returncode == 0, result.stderr
        assert "manual review; durable state remains unchanged" in result.stdout
        assert (tmp_path / "README.md").read_text(encoding="utf-8") == restored
    else:
        assert result.returncode == 1
        assert "recover_readme_proposal=true" in result.stdout
        assert "fresh workflow from updated main" in result.stdout
    assert (tmp_path / "reviewed-main-README.md").read_text(encoding="utf-8") == reviewed


@pytest.mark.parametrize("drift", [False, True])
def test_seal_adoption_still_accepts_only_the_initial_seal(tmp_path: Path, drift: bool) -> None:
    timestamp = datetime(2026, 9, 28, tzinfo=UTC)
    current = projection(tmp_path, timestamp)
    legacy = "".join(
        line for line in current.splitlines(keepends=True) if not line.startswith(STATE_SEAL_PREFIX)
    )
    restored = projection(tmp_path, timestamp + timedelta(days=1)) if drift else current
    result = run_review_gate(tmp_path, legacy, restored, adopt=True)
    assert result.returncode == (1 if drift else 0), result.stderr


@pytest.mark.parametrize(("adopt", "recover"), [(False, False), (True, False), (False, True)])
def test_render_failure_cannot_be_recovered(tmp_path: Path, adopt: bool, recover: bool) -> None:
    result = run_review_gate(
        tmp_path, "reviewed", "candidate", adopt=adopt, recover=recover, render_status=3
    )
    assert result.returncode == 3
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "reviewed"


def test_recovery_mode_guard_precedes_restore_and_forbids_side_effects() -> None:
    steps = process_steps()
    guard = process_step("Keep README recovery modes read-only")
    assert guard["if"] == (
        "(inputs.adopt_public_review_seal && inputs.recover_readme_proposal) || "
        "((inputs.adopt_public_review_seal || inputs.recover_readme_proposal) && "
        "(inputs.run_availability || inputs.run_scrape || inputs.add_manual_jobs || "
        "inputs.deploy_to_vps || inputs.readme_artifact_name == ''))"
    )
    assert "exit 1" in str(guard["run"])
    assert steps.index(guard) < steps.index(process_step("Restore verified canonical state"))

    for name in (
        "Configure restricted VPS snapshot access",
        "Publish and restore-verify VPS canonical snapshot",
    ):
        assert process_step(name)["if"] == (
            "inputs.adopt_public_review_seal != true && inputs.recover_readme_proposal != true"
        )

    validation = process_step("Validate database and generated projections")
    handoff = process_step("Upload README handoff")
    assert "if" not in validation
    assert validation["run"] == "uv run opportunities validate"
    assert steps.index(validation) < steps.index(handoff)
    assert handoff["if"] == "inputs.readme_artifact_name != ''"


def test_recovery_requires_explicit_dispatch_and_manual_readme_only_review() -> None:
    drill = yaml.load(
        (WORKFLOWS / "canonical-state-drill.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    processor = yaml.load(
        (WORKFLOWS / "reusable-process-state.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    for inputs in (
        drill["on"]["workflow_dispatch"]["inputs"],
        processor["on"]["workflow_call"]["inputs"],
    ):
        assert inputs["recover_readme_proposal"]["default"] == "false"
        assert inputs["recover_readme_proposal"]["type"] == "boolean"
    assert drill["concurrency"] == workflow("nightly.yml")["concurrency"]
    processing = drill["jobs"]["verify-recovery"]
    assert processing["permissions"] == {"contents": "read"}
    assert processing["with"]["require_crawl_authorization"] == "false"
    assert processing["with"]["recover_readme_proposal"] == "${{ inputs.recover_readme_proposal }}"
    for flag in ("run_availability", "run_scrape", "add_manual_jobs", "deploy_to_vps"):
        assert flag not in processing["with"]

    proposal = drill["jobs"]["propose-readme-recovery"]
    assert proposal["if"] == "inputs.recover_readme_proposal"
    assert proposal["needs"] == "verify-recovery"
    assert proposal["uses"] == "$/.github/workflows/reusable-readme-pr.yml"
    assert "secrets" not in proposal
    assert proposal["with"]["auto_merge"] == "false"
    assert proposal["with"]["branch"] == "automated/readme-recovery"
    assert proposal["with"]["artifact_name"] == (
        "opportunities-recovery-readme-${{ github.run_id }}"
    )
    assert processing["with"]["readme_artifact_name"] == (
        "${{ (inputs.adopt_public_review_seal || inputs.recover_readme_proposal) && "
        "format('opportunities-recovery-readme-{0}', github.run_id) || '' }}"
    )
    # Ordinary nightly runs still fail closed instead of automatically approving drift.
    assert "recover_readme_proposal:" not in (WORKFLOWS / "nightly.yml").read_text(encoding="utf-8")
