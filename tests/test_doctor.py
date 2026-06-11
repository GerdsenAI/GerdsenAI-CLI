"""The /doctor health-check command.

Drives DoctorCommand.execute with a stubbed llm_client (no network) and asserts
the ✅/❌ lines and the install hints. Pure-function, terminal output captured.
"""

from __future__ import annotations

from typing import Any

import pytest

from gerdsenai_cli.commands.system import DoctorCommand
from gerdsenai_cli.config.settings import Settings


class _StubClient:
    """Minimal llm_client exposing only health_check."""

    def __init__(self, connected: bool) -> None:
        self._connected = connected

    async def health_check(self) -> dict[str, Any]:
        return {
            "server_url": "http://localhost:11434",
            "connected": self._connected,
            "models_available": 3 if self._connected else 0,
            "response_time_ms": 12 if self._connected else None,
            "error": None if self._connected else "connection refused",
        }


@pytest.mark.asyncio
async def test_doctor_reports_connected(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = {"llm_client": _StubClient(True), "settings": Settings()}
    result = await DoctorCommand().execute({}, ctx)
    assert result.success
    assert result.data["llm_connected"] is True
    out = capsys.readouterr().out
    assert "Doctor" in out
    assert "Connected" in out


@pytest.mark.asyncio
async def test_doctor_disconnected_shows_setup_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = {"llm_client": _StubClient(False), "settings": Settings()}
    result = await DoctorCommand().execute({}, ctx)
    assert result.data["llm_connected"] is False
    out = capsys.readouterr().out
    assert "Disconnected" in out
    assert "setup" in out.lower()  # the "start your server / run /setup" hint


@pytest.mark.asyncio
async def test_doctor_missing_extra_shows_install_hint(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pretend every optional extra is absent.
    monkeypatch.setattr(DoctorCommand, "_installed", staticmethod(lambda module: False))
    ctx = {"llm_client": _StubClient(True), "settings": Settings()}
    await DoctorCommand().execute({}, ctx)
    out = capsys.readouterr().out
    assert "missing" in out
    assert "MCP tool servers" in out
    assert "pip install" in out


@pytest.mark.asyncio
async def test_doctor_native_tools_for_capable_model(
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = Settings()
    settings.current_model = "gpt-4"  # recognized as tool-capable
    ctx = {"llm_client": _StubClient(True), "settings": settings}
    await DoctorCommand().execute({}, ctx)
    out = capsys.readouterr().out
    assert "native" in out.lower()


@pytest.mark.asyncio
async def test_doctor_reports_delegation_settings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ctx = {"llm_client": _StubClient(True), "settings": Settings()}
    await DoctorCommand().execute({}, ctx)
    out = capsys.readouterr().out
    assert "Delegation" in out
