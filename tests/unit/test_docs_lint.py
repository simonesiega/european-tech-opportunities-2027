"""Offline checks for the maintained Markdown scope and pinned lint runners."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from scripts.docs import lint_docs


def test_documentation_linters_use_the_same_curated_read_only_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lint_docs, "ROOT", tmp_path)
    monkeypatch.setattr("scripts.docs.lint_docs.shutil.which", lambda _name: "docker")
    monkeypatch.setattr(sys, "argv", ["lint_docs.py"])
    for file in lint_docs.ROOT_FILES:
        path = tmp_path / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Maintained\n", encoding="utf-8")
    guide = tmp_path / "docs/maintainers/engineering/guide.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "docs/reference.md").write_text("# Maintained\n", encoding="utf-8")
    for filename in ("README.md", "source.md"):
        diagram = tmp_path / "docs/assets/diagram" / filename
        diagram.parent.mkdir(parents=True, exist_ok=True)
        diagram.write_text("# Diagram\n", encoding="utf-8")
    for excluded in (
        "docs/generated/report.md",
        "docs/vendor/upstream.md",
        "docs/assets/listings/third-party.md",
        "docs/assets/promo/.work/review.md",
        "docs/assets/promo/node_modules/dependency/README.md",
    ):
        path = tmp_path / excluded
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Not maintained\n", encoding="utf-8")
    template = tmp_path / ".github/ISSUE_TEMPLATE/question.md"
    template.parent.mkdir(parents=True)
    template.write_text("# Question\n", encoding="utf-8")

    commands: list[list[str]] = []

    def run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert not check
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("scripts.docs.lint_docs.subprocess.run", run)
    assert lint_docs.main() == 0
    assert len(commands) == 2
    for command in commands:
        assert command[:5] == ["docker", "run", "--rm", "--network", "none"]
        assert f"type=bind,source={tmp_path},target=/workdir,readonly" in command
        assert "docs/maintainers/engineering/guide.md" in command
        assert "docs/reference.md" in command
        assert "docs/assets/diagram/README.md" in command
        assert "docs/assets/diagram/source.md" in command
        assert "docs/assets/promo/maintainers/VIDEO.md" in command
        # Name inventories explicitly so shrinking ROOT_FILES cannot weaken this check.
        assert ".github/WORKFLOWS.md" in command
        assert "scripts/SCRIPT.md" in command
        assert "tests/TEST.md" in command
        assert ".github/ISSUE_TEMPLATE/question.md" in command
        assert "docs/generated/report.md" not in command
        assert "docs/vendor/upstream.md" not in command
        assert "docs/assets/listings/third-party.md" not in command
        assert "docs/assets/promo/.work/review.md" not in command
        assert "docs/assets/promo/node_modules/dependency/README.md" not in command
        assert all(file in command for file in lint_docs.ROOT_FILES)
    assert lint_docs.MARKDOWNLINT in commands[0]
    assert lint_docs.VALE in commands[1]


def test_documentation_lint_stops_after_failed_markdownlint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lint_docs, "ROOT", tmp_path)
    monkeypatch.setattr(lint_docs, "ROOT_FILES", ())
    monkeypatch.setattr("scripts.docs.lint_docs.shutil.which", lambda _name: "docker")
    monkeypatch.setattr(sys, "argv", ["lint_docs.py"])
    guide = tmp_path / "docs/users/browsing/guide.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Guide\n", encoding="utf-8")
    commands: list[list[str]] = []

    def run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr("scripts.docs.lint_docs.subprocess.run", run)
    assert lint_docs.main() == 1
    assert len(commands) == 1


@pytest.mark.parametrize("problem", ["missing-docker", "missing-document"])
def test_documentation_lint_preflight_fails_without_starting_a_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    problem: str,
) -> None:
    monkeypatch.setattr(lint_docs, "ROOT", tmp_path)
    monkeypatch.setattr(lint_docs, "ROOT_FILES", ("missing.md",))
    monkeypatch.setattr(
        "scripts.docs.lint_docs.shutil.which",
        lambda _name: None if problem == "missing-docker" else "docker",
    )
    monkeypatch.setattr(sys, "argv", ["lint_docs.py"])

    def unexpected_run(
        command: list[str], *, cwd: Path, check: bool
    ) -> subprocess.CompletedProcess[str]:
        raise AssertionError("Preflight errors must not launch containers")

    monkeypatch.setattr("scripts.docs.lint_docs.subprocess.run", unexpected_run)
    with pytest.raises(SystemExit) as error:
        lint_docs.main()
    assert error.value.code == 2
    diagnostic = capsys.readouterr().err
    assert (
        "Docker is required" if problem == "missing-docker" else "file is missing"
    ) in diagnostic
