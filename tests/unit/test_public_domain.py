"""Guard against accidentally publishing the retired hostname as a canonical URL."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_HOST = "opportunities2027" + ".simonesiega.com"
# Only redirect configuration, validation, migration documentation, and redirect tests
# may refer to the retired hostname. All other public links must use the new origin.
LEGACY_REFERENCES = {
    ".github/workflows/docker-ci.yml",
    "docs/maintainers/operations/deployment.md",
    "site/next.config.ts",
    "site/src/lib/site-url-value.ts",
    "site/tests/unit/site-url-value.test.ts",
    "site/tests/e2e/directory.spec.ts",
}


def test_legacy_hostname_only_in_redirect_and_migration_material() -> None:
    tracked = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            timeout=30,
        )
        .decode()
        .split("\0")
    )
    references = {
        name
        for name in tracked
        if name
        and (ROOT / name).is_file()
        and LEGACY_HOST in (ROOT / name).read_bytes().decode("utf-8", errors="replace")
    }
    # Removing obsolete migration references is allowed; introducing others is not.
    assert references <= LEGACY_REFERENCES, references - LEGACY_REFERENCES
