"""Guard against accidentally publishing the retired hostname as a canonical URL."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_HOST = "opportunities2027" + ".simonesiega.com"
CANONICAL_ORIGIN = "https://techopportunities.eu"
# Only redirect configuration, validation, migration documentation, and redirect tests
# may refer to the retired hostname. All other public links must use the new origin.
LEGACY_REFERENCES = {
    ".github/workflows/docker-ci.yml",
    "README.md",
    "docs/guides/operations/docker.md",
    "docs/guides/user-guide/website.md",
    "site/next.config.ts",
    "site/src/lib/site-url-value.ts",
    "site/tests/unit/site-url-value.test.ts",
    "site/tests/e2e/directory.spec.ts",
}


def test_legacy_hostname_only_in_redirect_and_migration_material() -> None:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    references = {
        name
        for name in tracked
        if name
        and (ROOT / name).is_file()
        and LEGACY_HOST in (ROOT / name).read_bytes().decode("utf-8", errors="replace")
    }
    assert references == LEGACY_REFERENCES


def test_canonical_origin_across_public_projections() -> None:
    for name in (
        "src/opportunities/readme.py",
        "site/src/lib/site-config.ts",
        "Dockerfile",
        ".github/workflows/site-ci.yml",
        ".github/workflows/docker-ci.yml",
        "pyproject.toml",
        "README.md",
    ):
        content = (ROOT / name).read_text(encoding="utf-8")
        expected = (
            "techopportunities.eu" if name == "site/src/lib/site-config.ts" else CANONICAL_ORIGIN
        )
        assert expected in content
        if name not in LEGACY_REFERENCES:
            assert LEGACY_HOST not in content
