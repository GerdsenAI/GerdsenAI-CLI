"""Bridge auth: LLMClient injects a bearer header when a key is configured,
and stays unauthenticated (local-first) when none is set."""
from __future__ import annotations

import pytest

from gerdsenai_cli.config.settings import Settings
from gerdsenai_cli.core.llm_client import LLMClient


@pytest.mark.asyncio
async def test_bearer_header_from_env_takes_precedence(monkeypatch):
    """GERDSENAI_LLM_API_KEY is injected as 'Authorization: Bearer ...'"""
    monkeypatch.setenv("GERDSENAI_LLM_API_KEY", "sk-env-key")
    settings = Settings(llm_server_url="http://gateway.example:4000")
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert client.client.headers.get("Authorization") == "Bearer sk-env-key"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_bearer_header_from_settings_when_no_env(monkeypatch):
    """settings.api_key is used when the env var is absent"""
    monkeypatch.delenv("GERDSENAI_LLM_API_KEY", raising=False)
    settings = Settings(
        llm_server_url="http://gateway.example:4000", api_key="sk-settings-key"
    )
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert client.client.headers.get("Authorization") == "Bearer sk-settings-key"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_no_auth_header_when_unset(monkeypatch):
    """No key anywhere -> no Authorization header (unauthenticated local servers work)"""
    monkeypatch.delenv("GERDSENAI_LLM_API_KEY", raising=False)
    settings = Settings(llm_server_url="http://localhost:11434")
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert "Authorization" not in client.client.headers
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_empty_env_string_falls_back_to_no_header(monkeypatch):
    """An empty GERDSENAI_LLM_API_KEY string must not produce a bogus 'Bearer ' header"""
    monkeypatch.setenv("GERDSENAI_LLM_API_KEY", "")
    settings = Settings(llm_server_url="http://localhost:11434")
    client = LLMClient(settings)
    await client.__aenter__()
    try:
        assert "Authorization" not in client.client.headers
    finally:
        await client.__aexit__(None, None, None)
