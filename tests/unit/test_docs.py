from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def test_workflow_checker_validates_only_the_local_workflow_overview(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts"
    guide = tmp_path / "docs" / "guides" / "operations" / "automation.md"
    workflow_dir = tmp_path / ".github" / "workflows"
    script_dir.mkdir()
    guide.parent.mkdir(parents=True)
    workflow_dir.mkdir(parents=True)
    for name in ("README.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md"):
        (tmp_path / name).write_text(f"# {name}\n", encoding="utf-8")
    shutil.copyfile(
        Path(__file__).parents[2] / "scripts" / "check_docs.py", script_dir / "check_docs.py"
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
