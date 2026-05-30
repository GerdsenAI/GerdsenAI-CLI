"""Tests for the Anthropic provider, secret storage, and /anthropic command."""

from __future__ import annotations

from typing import Any

import pytest

from gerdsenai_cli.commands.anthropic_cmd import AnthropicCommand
from gerdsenai_cli.core import secrets
from gerdsenai_cli.core.providers.anthropic import (
    AnthropicProvider,
    _supports_temperature,
)

# --------------------------------------------------------------------------- #
# secrets
# --------------------------------------------------------------------------- #


class FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, name: str) -> str | None:
        return self.store.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.store[(service, name)] = value

    def delete_password(self, service: str, name: str) -> None:
        del self.store[(service, name)]


def test_secret_roundtrip_via_keyring(monkeypatch: Any) -> None:
    fake = FakeKeyring()
    monkeypatch.setattr(secrets, "_keyring", lambda: fake)
    assert secrets.get_secret("anthropic") is None
    assert secrets.set_secret("anthropic", "sk-test") is True
    assert secrets.get_secret("anthropic") == "sk-test"
    assert secrets.secret_source("anthropic") == "keyring"
    assert secrets.delete_secret("anthropic") is True
    assert secrets.get_secret("anthropic") is None


def test_secret_env_fallback(monkeypatch: Any) -> None:
    monkeypatch.setattr(secrets, "_keyring", lambda: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    assert secrets.get_secret("anthropic") == "env-key"
    assert secrets.secret_source("anthropic") == "env"
    # set_secret without a keyring backend reports failure (no silent config write)
    assert secrets.set_secret("anthropic", "x") is False


def test_secret_none_when_unset(monkeypatch: Any) -> None:
    monkeypatch.setattr(secrets, "_keyring", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert secrets.get_secret("anthropic") is None
    assert secrets.secret_source("anthropic") is None


# --------------------------------------------------------------------------- #
# provider request building
# --------------------------------------------------------------------------- #


def test_supports_temperature() -> None:
    assert _supports_temperature("claude-sonnet-4-6") is True
    assert _supports_temperature("claude-opus-4-6") is True
    assert _supports_temperature("claude-opus-4-7") is False
    assert _supports_temperature("claude-opus-4-8") is False


def test_build_kwargs_caches_system_and_omits_temperature() -> None:
    p = AnthropicProvider()
    msgs = [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
    ]
    kw = p._build_kwargs(msgs, "claude-opus-4-8", 0.7, 256, ["STOP"])
    # System is lifted out and cache-controlled.
    assert kw["system"][0]["text"] == "be terse"
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    # Only the non-system turn remains.
    assert kw["messages"] == [{"role": "user", "content": "hi"}]
    assert kw["stop_sequences"] == ["STOP"]
    assert kw["max_tokens"] == 256
    # Opus 4.8 rejects temperature -> omitted.
    assert "temperature" not in kw


def test_build_kwargs_includes_temperature_for_supported_model() -> None:
    p = AnthropicProvider()
    kw = p._build_kwargs(
        [{"role": "user", "content": "hi"}], "claude-sonnet-4-6", 0.3, None, None
    )
    assert kw["temperature"] == 0.3
    assert kw["max_tokens"] == 4096  # default when not provided
    assert "system" not in kw  # no system message


# --------------------------------------------------------------------------- #
# provider with a mocked SDK client
# --------------------------------------------------------------------------- #


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Stream:
    async def __aenter__(self) -> _Stream:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    @property
    async def text_stream(self):  # type: ignore[no-untyped-def]
        for chunk in ["Hel", "lo"]:
            yield chunk


class _Messages:
    async def create(self, **kwargs: Any) -> Any:
        class _R:
            content = [_Block("Hello")]

        return _R()

    def stream(self, **kwargs: Any) -> _Stream:
        return _Stream()


class _Model:
    def __init__(self, mid: str) -> None:
        self.id = mid


class _Models:
    async def list(self):  # type: ignore[no-untyped-def]
        for mid in ["claude-opus-4-8", "claude-haiku-4-5"]:
            yield _Model(mid)


class FakeClient:
    def __init__(self) -> None:
        self.messages = _Messages()
        self.models = _Models()


@pytest.mark.asyncio
async def test_detect_requires_key(monkeypatch: Any) -> None:
    # The anthropic SDK is an optional extra and may be absent in the test env;
    # inject a stub so detect() exercises the key logic, not the import guard.
    import sys
    import types

    monkeypatch.setitem(sys.modules, "anthropic", types.ModuleType("anthropic"))
    monkeypatch.setattr(
        "gerdsenai_cli.core.providers.anthropic.get_secret", lambda _n: None
    )
    assert await AnthropicProvider().detect() is False
    assert await AnthropicProvider(api_key="sk-x").detect() is True


@pytest.mark.asyncio
async def test_chat_and_stream(monkeypatch: Any) -> None:
    p = AnthropicProvider(api_key="sk-x")
    p._client = lambda: FakeClient()  # type: ignore[method-assign]

    text = await p.chat_completion(
        [{"role": "user", "content": "hi"}], "claude-opus-4-8"
    )
    assert text == "Hello"

    chunks = [
        c
        async for c in p.stream_completion(
            [{"role": "user", "content": "hi"}], "claude-opus-4-8"
        )
    ]
    assert "".join(chunks) == "Hello"


@pytest.mark.asyncio
async def test_list_models_live_then_fallback(monkeypatch: Any) -> None:
    p = AnthropicProvider(api_key="sk-x")
    p._client = lambda: FakeClient()  # type: ignore[method-assign]
    live = await p.list_models()
    assert {m.name for m in live} == {"claude-opus-4-8", "claude-haiku-4-5"}

    def _boom() -> Any:
        raise RuntimeError("no network")

    p._client = _boom  # type: ignore[method-assign]
    fallback = await p.list_models()
    assert any(m.name == "claude-sonnet-4-6" for m in fallback)  # known list


# --------------------------------------------------------------------------- #
# /anthropic command
# --------------------------------------------------------------------------- #


def test_command_parse_arguments() -> None:
    cmd = AnthropicCommand()
    assert cmd.parse_arguments("") == {"action": "status", "value": ""}
    assert cmd.parse_arguments("set-key sk-123") == {
        "action": "set-key",
        "value": "sk-123",
    }
    assert cmd.parse_arguments("chat hello there") == {
        "action": "chat",
        "value": "hello there",
    }
    assert cmd.parse_arguments("bogus") == {"action": "help", "value": ""}


@pytest.mark.asyncio
async def test_command_status_runs() -> None:
    result = await AnthropicCommand().execute({"action": "status", "value": ""})
    assert result.success


@pytest.mark.asyncio
async def test_command_chat_unavailable(monkeypatch: Any) -> None:
    # No key -> provider unavailable -> graceful message, success.
    monkeypatch.setattr(
        "gerdsenai_cli.core.providers.anthropic.get_secret", lambda _n: None
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await AnthropicCommand().execute({"action": "chat", "value": "hi"})
    assert result.success
    assert "unavailable" in (result.message or "").lower()
