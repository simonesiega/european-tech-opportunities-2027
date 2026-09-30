from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


def test_local_workflow_references_use_self_repository_syntax_and_exist() -> None:
    root = Path(__file__).parents[2]
    checked_references = 0
    for workflow in (root / ".github" / "workflows").glob("*.yml"):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*uses:\s*(\S+)", line)
            if match is None:
                continue
            reference = match.group(1)
            assert not reference.startswith("./.github/"), (
                f"{workflow.relative_to(root)} must use GitHub self-repository syntax: {reference}"
            )
            if reference.startswith("$/.github/"):
                checked_references += 1
                assert (root / reference[2:]).exists(), (
                    f"{workflow.relative_to(root)} references a missing local action: {reference}"
                )
    assert checked_references > 0


def test_source_checker_validates_script_inventory_and_local_workflow_overview(
    tmp_path: Path,
) -> None:
    script_dir = tmp_path / "scripts" / "docs"
    guide = tmp_path / "docs" / "maintainers" / "operations" / "automation.md"
    workflow_dir = tmp_path / ".github" / "workflows"
    script_dir.mkdir(parents=True)
    guide.parent.mkdir(parents=True)
    workflow_dir.mkdir(parents=True)
    for name in (
        "README.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "PRIVACY.md",
        "CODE_OF_CONDUCT.md",
    ):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    shutil.copyfile(
        Path(__file__).parents[2] / "scripts" / "docs" / "check_docs.py",
        script_dir / "check_docs.py",
    )
    (workflow_dir / "python-ci.yml").write_text("name: Python CI\n", encoding="utf-8")
    guide.write_text(
        """# Automation

## Workflow overview

| Workflow | Trigger |
|---|---|
| `python-ci.yml` | Push |

External repositories may also use `external.yml`.
An example path is `examples/example.yml`, generated output may mention `generated.yml`,
and `settings.yml` is not a workflow reference.

## Next section
""",
        encoding="utf-8",
    )

    valid = subprocess.run(
        [sys.executable, str(script_dir / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid.returncode == 0, valid.stderr

    inventory = tmp_path / "scripts" / "SCRIPT.md"
    inventory.write_text("# Scripts\n\n[Missing helper](missing.py)\n", encoding="utf-8")
    invalid_inventory = subprocess.run(
        [sys.executable, str(script_dir / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid_inventory.returncode == 1
    assert "missing missing.py" in invalid_inventory.stderr
    (inventory.parent / "missing.py").write_text("# Offline helper\n", encoding="utf-8")
    valid_inventory = subprocess.run(
        [sys.executable, str(script_dir / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid_inventory.returncode == 0, valid_inventory.stderr

    guide.write_text(
        """# Automation

## Workflow overview

| Workflow | Trigger |
|---|---|
| `missing.yml` | Push |
""",
        encoding="utf-8",
    )
    invalid = subprocess.run(
        [sys.executable, str(script_dir / "check_docs.py")],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert invalid.returncode == 1
    assert "missing workflow missing.yml" in invalid.stderr


def test_source_links_cover_images_video_and_agent_guidance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts.docs import check_docs

    document = tmp_path / "AGENTS.md"
    document.write_text(
        "# Agents\n![Diagram](architecture.svg)\n"
        '<video poster="poster.webp"><source src="tour.mp4"></video>\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "ROOT", tmp_path)
    monkeypatch.setattr(check_docs, "MARKDOWN_FILES", (document,))
    monkeypatch.setattr(check_docs, "AUTOMATION_GUIDE", document)
    assert check_docs.main() == 1
    assert capsys.readouterr().err.count("missing") == 3
    for filename in ("architecture.svg", "poster.webp", "tour.mp4"):
        (tmp_path / filename).write_bytes(b"public fixture")
    assert check_docs.main() == 0


@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("docs/assets/diagram/README.md", False),
        ("docs/assets/diagram/source.md", False),
        ("docs/assets/diagram/svg/repository.svg", True),
        ("docs/assets/logo/Opportunities.webp", True),
        (r"docs\assets\diagram\README.md", False),
        (r"docs\assets\diagram\svg\repository.svg", True),
    ],
)
def test_external_link_scope_keeps_authored_diagram_markdown(path: str, excluded: bool) -> None:
    config = tomllib.loads((Path(__file__).parents[2] / "lychee.toml").read_text(encoding="utf-8"))
    assert any(re.search(pattern, path) for pattern in config["exclude_path"]) is excluded
