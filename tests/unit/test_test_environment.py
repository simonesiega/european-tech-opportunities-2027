"""Offline checks for the test harness's own source-access and isolation boundaries."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest

from opportunities.config.settings import load_settings
from tests.conftest import live_tests_enabled
from tests.shell_helpers import offline_shell_environment


@pytest.mark.parametrize("selection", ["", "not live", "live or performance", "live"])
@pytest.mark.parametrize("opt_in", [None, "0", "1"])
@pytest.mark.parametrize("permission", [None, "false", "true"])
def test_live_gate_requires_explicit_selection_and_both_flags(
    selection: str, opt_in: str | None, permission: str | None
) -> None:
    # Evaluate synthetic mappings; never activate source-authorization environment variables.
    environment = {
        key: value
        for key, value in {
            "OPPORTUNITIES_LIVE_TESTS": opt_in,
            "OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED": permission,
        }.items()
        if value is not None
    }
    assert live_tests_enabled(selection, environment) is (
        selection == "live" and opt_in == "1" and permission == "true"
    )


def test_default_test_environment_is_disposable_and_unauthorized(tmp_path: Path) -> None:
    assert Path.cwd() == tmp_path
    assert Path.home() == tmp_path / "home"
    assert not any(
        name.startswith(("OPPORTUNITIES_", "CANONICAL_STATE_", "VPS_", "RELEASE_"))
        for name in os.environ
    )
    assert not (tmp_path / ".env").exists()
    assert load_settings().linkedin_crawl_authorized is False


def test_offline_http_guard_blocks_sync_and_async_default_transports() -> None:
    # Even if the guard regresses, this reserved local port cannot contact an external source.
    url = "http://127.0.0.1:1/"

    def request_ignoring_application_errors(client: httpx.Client) -> None:
        try:
            client.get(url)
        except Exception:
            return  # The guard must fail the test even through this error-handling path.

    with (
        httpx.Client(trust_env=False) as client,
        pytest.raises(pytest.fail.Exception, match="real HTTP is disabled"),
    ):
        request_ignoring_application_errors(client)

    async def run() -> None:
        async with httpx.AsyncClient(trust_env=False) as client:
            with pytest.raises(pytest.fail.Exception, match="real HTTP is disabled"):
                await client.get(url)

    asyncio.run(run())


def test_offline_http_guard_preserves_injected_mock_transports() -> None:
    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="synthetic")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert client.get("https://example.invalid/").text == "synthetic"


def test_shell_subprocesses_get_only_isolated_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VPS_HOST", "operator.invalid")
    monkeypatch.setenv("CANONICAL_STATE_DATABASE", "/not-a-test-database")
    monkeypatch.setenv("OPPORTUNITIES_SETTINGS_FILE", "/not-a-test-settings-file")
    environment = offline_shell_environment(tmp_path)
    assert "VPS_HOST" not in environment
    assert "CANONICAL_STATE_DATABASE" not in environment
    assert "OPPORTUNITIES_SETTINGS_FILE" not in environment
    assert environment["HOME"] == str(tmp_path / "home")
    assert environment["RUNNER_TEMP"] == str(tmp_path)
    assert environment["UV_OFFLINE"] == "1"
    first_bin = Path(environment["PATH"].split(os.pathsep)[0])
    for command in ("ssh", "scp", "sftp"):
        assert (first_bin / command).is_file()
