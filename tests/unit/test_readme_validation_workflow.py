"""Offline execution of README validation dispatch and dependency-review scope guards."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.shell_helpers import offline_shell_environment

WORKFLOWS = Path(__file__).parents[2] / ".github" / "workflows"
HEAD_SHA = "0123456789012345678901234567890123456789"
BASE_SHA = "abcdef0123456789abcdef0123456789abcdef01"
BRANCH = "automated/nightly-full-update"
VALIDATION_WORKFLOWS = (
    "python-ci.yml",
    "site-ci.yml",
    "docker-ci.yml",
    "codeql.yml",
    "gitleaks.yml",
    "documentation.yml",
    "dependency-review.yml",
)


def workflow_steps(filename: str, job: str) -> list[dict[str, object]]:
    document = yaml.load((WORKFLOWS / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps: list[dict[str, object]] = document["jobs"][job]["steps"]
    return steps


def pull_request_metadata() -> dict[str, object]:
    return {
        "state": "OPEN",
        "baseRefName": "main",
        "baseRefOid": BASE_SHA,
        "headRefName": BRANCH,
        "headRefOid": HEAD_SHA,
        "isCrossRepository": False,
        "title": "data: nightly update",
        "files": [{"path": "README.md"}],
    }


def run_script(
    tmp_path: Path, script: str, fakes: str, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    if bash is None or shutil.which("jq") is None:
        pytest.skip("README validation workflow tests require Bash and jq")
    result = subprocess.run(
        [bash, "-c", fakes + script],
        cwd=tmp_path,
        env={
            **offline_shell_environment(tmp_path),
            "GITHUB_REPOSITORY": "synthetic/repository",
            "GITHUB_REF": f"refs/heads/{BRANCH}",
            "GITHUB_SHA": HEAD_SHA,
            "GITHUB_OUTPUT": (tmp_path / "outputs").as_posix(),
            "CALLS_FILE": (tmp_path / "calls.log").as_posix(),
            **environment,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert not (tmp_path / "blocked-network.log").exists(), result.stderr
    return result


def run_review_guard(
    tmp_path: Path, metadata: dict[str, object], **environment: str
) -> subprocess.CompletedProcess[str]:
    step = next(
        step
        for step in workflow_steps("dependency-review.yml", "dependency-review")
        if step.get("id") == "review-refs"
    )
    script = step["run"]
    assert isinstance(script, str)
    fakes = """
gh() {
  printf '%s\\n' "$*" >> "$CALLS_FILE"
  local expected="pr view $PULL_REQUEST_NUMBER --repo $GITHUB_REPOSITORY"
  expected+=" --json state,baseRefName,baseRefOid,headRefName,headRefOid,isCrossRepository,files"
  if [ "$*" != "$expected" ]; then return 97; fi
  if [ "$LOOKUP_STATUS" != "0" ]; then return "$LOOKUP_STATUS"; fi
  printf '%s\\n' "$PR_METADATA"
}
"""
    return run_script(
        tmp_path,
        script,
        fakes,
        {
            "PULL_REQUEST_NUMBER": "123",
            "PR_METADATA": json.dumps(metadata),
            "LOOKUP_STATUS": "0",
            **environment,
        },
    )


def test_dependency_review_preserves_real_action_and_pull_request_validation() -> None:
    document = yaml.load(
        (WORKFLOWS / "dependency-review.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert document["on"]["pull_request"] == ""
    inputs = document["on"]["workflow_dispatch"]["inputs"]
    assert list(inputs) == ["pull_request_number"]
    assert inputs["pull_request_number"]["required"] == "true"
    assert inputs["pull_request_number"]["type"] == "string"
    assert document["permissions"] == {"contents": "read", "pull-requests": "read"}
    job = document["jobs"]["dependency-review"]
    assert "if" not in job
    assert "continue-on-error" not in job
    checkout, guard, action = job["steps"]
    assert checkout["with"]["persist-credentials"] == "false"
    assert guard["if"] == "github.event_name == 'workflow_dispatch'"
    assert guard["env"]["PULL_REQUEST_NUMBER"] == "${{ inputs.pull_request_number }}"
    assert action["uses"] == (
        "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294"
    )
    assert "if" not in action
    assert "continue-on-error" not in action
    assert action["with"] == {
        "base-ref": (
            "${{ steps.review-refs.outputs.base_sha || github.event.pull_request.base.sha }}"
        ),
        "head-ref": (
            "${{ steps.review-refs.outputs.head_sha || github.event.pull_request.head.sha }}"
        ),
        "fail-on-severity": "high",
        "fail-on-scopes": "runtime, development, unknown",
        "license-check": "false",
        "show-openssf-scorecard": "false",
    }


def test_dispatch_resolves_real_pr_base_and_binds_head_to_workflow_commit(tmp_path: Path) -> None:
    result = run_review_guard(tmp_path, pull_request_metadata())
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "outputs").read_text(encoding="utf-8") == (
        f"base_sha={BASE_SHA}\nhead_sha={HEAD_SHA}\n"
    )
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert len(calls) == 1
    assert calls[0].startswith("pr view 123 --repo synthetic/repository --json ")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state", "CLOSED"),
        ("state", "MERGED"),
        ("baseRefName", "other-base"),
        ("isCrossRepository", True),
        ("isCrossRepository", None),
        ("headRefName", "automated/other-proposal"),
        ("headRefOid", "1" * 40),
        ("baseRefOid", HEAD_SHA),
        ("baseRefOid", "main"),
        ("baseRefOid", ""),
        ("baseRefOid", None),
        ("baseRefOid", BASE_SHA + "\n"),
        ("baseRefOid", HEAD_SHA + "\n"),
        ("baseRefOid", BASE_SHA + "\ninjected=output"),
        ("files", []),
        ("files", [{"path": "README.md"}, {"path": "pyproject.toml"}]),
        ("files", [{"path": "other/README.md"}]),
    ],
)
def test_dependency_dispatch_rejects_untrusted_scope_or_comparison(
    tmp_path: Path, field: str, value: object
) -> None:
    metadata = pull_request_metadata()
    metadata[field] = value
    result = run_review_guard(tmp_path, metadata)
    assert result.returncode != 0
    assert "failed the README-only PR scope or commit check" in result.stdout
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PULL_REQUEST_NUMBER", ""),
        ("PULL_REQUEST_NUMBER", "0"),
        ("PULL_REQUEST_NUMBER", "-1"),
        ("PULL_REQUEST_NUMBER", "https://github.com/other/repository/pull/123"),
        ("PULL_REQUEST_NUMBER", "123; exit 0"),
        ("GITHUB_REF", "refs/heads/main"),
        ("GITHUB_REF", "refs/tags/automated/nightly-full-update"),
        ("GITHUB_REF", "refs/heads/contributor-branch"),
        ("GITHUB_SHA", "main"),
        ("GITHUB_SHA", HEAD_SHA + "\ninjected=output"),
    ],
)
def test_dependency_dispatch_rejects_invalid_inputs_before_api_access(
    tmp_path: Path, name: str, value: str
) -> None:
    result = run_review_guard(tmp_path, pull_request_metadata(), **{name: value})
    assert result.returncode != 0
    assert not (tmp_path / "calls.log").exists()
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize("scenario", ["api-error", "malformed-json", "missing-metadata"])
def test_dependency_dispatch_fails_closed_on_unavailable_metadata(
    tmp_path: Path, scenario: str
) -> None:
    environment = {
        "api-error": {"LOOKUP_STATUS": "1"},
        "malformed-json": {"PR_METADATA": "not JSON"},
        "missing-metadata": {"PR_METADATA": "{}"},
    }[scenario]
    result = run_review_guard(tmp_path, pull_request_metadata(), **environment)
    assert result.returncode != 0
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize(
    "scenario",
    [
        "success",
        "dispatch-failed",
        "dependency-failed",
        "dependency-missing",
        "dependency-wrong-sha",
        "dependency-stale-run",
        "scope-changed",
    ],
)
def test_readme_dispatch_waits_for_dependency_review_before_merge(
    tmp_path: Path, scenario: str
) -> None:
    script = workflow_steps("reusable-readme-pr.yml", "propose")[-1]["run"]
    assert isinstance(script, str)
    start = script.index("validation_workflows=(")
    assert script.index("README pull request failed the exact-scope safety check.") < start
    runs: list[dict[str, object]] = [
        {
            "workflow": name,
            "databaseId": 100 + index,
            "createdAt": "2026-10-03T22:06:01Z",
            "headSha": HEAD_SHA,
        }
        for index, name in enumerate(VALIDATION_WORKFLOWS)
    ]
    if scenario == "dependency-missing":
        runs.pop()
    elif scenario == "dependency-wrong-sha":
        runs[-1]["headSha"] = "1" * 40
    elif scenario == "dependency-stale-run":
        runs[-1]["createdAt"] = "2026-10-03T22:05:59Z"
    metadata = pull_request_metadata()
    if scenario == "scope-changed":
        metadata["files"] = [{"path": "README.md"}, {"path": "pyproject.toml"}]
    # Execute the checked-in dispatch, lookup, wait, and merge logic. gh is fake,
    # but jq evaluates the actual run-selection and scope expressions on synthetic data.
    fakes = """
set -euo pipefail
pr_number=123
head_sha="$GITHUB_SHA"
UPDATE_BRANCH="${GITHUB_REF#refs/heads/}"
UPDATE_TITLE='data: nightly update'
date() { printf '%s\\n' '2026-10-03T22:06:00Z'; }
sleep() { :; }
gh() {
  printf '%s\\n' "$*" >> "$CALLS_FILE"
  case "$1 $2" in
    'workflow run')
      if [ "$SCENARIO" = dispatch-failed ] && [ "$3" = dependency-review.yml ]; then
        return 1
      fi
      ;;
    'run list')
      local expected="--workflow $4 --branch $UPDATE_BRANCH --event workflow_dispatch --limit 20"
      expected+=" --json databaseId,createdAt,headSha --jq ${!#}"
      if [ "${*:3}" != "$expected" ]; then return 97; fi
      printf '%s\\n' "$RUNS_JSON" | jq --arg workflow "$4" \
        'map(select(.workflow == $workflow))' | jq -r "${!#}"
      ;;
    'run watch')
      if [ "$*" != "run watch $3 --compact --exit-status" ]; then return 97; fi
      if [ "$SCENARIO" = dependency-failed ] && [ "$3" = 106 ]; then return 1; fi
      ;;
    'pr view') printf '%s\\n' "$PR_METADATA" ;;
    'api repos/synthetic/repository')
      if [ "$*" != 'api repos/synthetic/repository --jq .allow_auto_merge' ]; then return 97; fi
      printf '%s\\n' false
      ;;
    'pr merge') ;;
    *) return 97 ;;
  esac
}
"""
    result = run_script(
        tmp_path,
        script[start:],
        fakes,
        {
            "SCENARIO": scenario,
            "RUNS_JSON": json.dumps(runs),
            "PR_METADATA": json.dumps(metadata),
            "UPDATE_AUTO_MERGE": "true",
        },
    )
    assert result.returncode == (0 if scenario == "success" else 1), result.stderr
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    dispatches = [call for call in calls if call.startswith("workflow run ")]
    assert dispatches == [
        f"workflow run {name} --ref {BRANCH}"
        + (" --raw-field pull_request_number=123" if name == "dependency-review.yml" else "")
        for name in VALIDATION_WORKFLOWS
    ]
    merges = [call for call in calls if call.startswith("pr merge ")]
    if scenario == "success":
        assert merges == [f"pr merge 123 --squash --match-head-commit {HEAD_SHA}"]
        watches = [call for call in calls if call.startswith("run watch ")]
        assert watches == [f"run watch {100 + index} --compact --exit-status" for index in range(7)]
        assert calls.index(watches[-1]) < calls.index(merges[0])
    else:
        assert not merges
    if scenario in {"dependency-missing", "dependency-wrong-sha", "dependency-stale-run"}:
        assert "Could not identify the dependency-review.yml validation run" in result.stdout
    if scenario == "scope-changed":
        assert "scope changed during validation" in result.stdout


def test_all_readme_validation_workflows_accept_explicit_dispatch() -> None:
    for name in VALIDATION_WORKFLOWS:
        document = yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        assert "workflow_dispatch" in document["on"], name
