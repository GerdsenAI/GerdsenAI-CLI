"""Environment-variable configuration overrides.

Covers the three env vars (precedence: CLI flag > environment > config file):

- ``GERDSENAI_CONFIG``           — alternate config file path (``--config`` wins)
- ``GERDSENAI_LLM_SERVER_URL``   — overrides ``llm_server_url`` at load time;
  a malformed value fails loudly (never a silent localhost fallback)
- ``GERDSENAI_MODEL``            — overrides ``current_model`` at load time and
  suppresses the first-run ``models[0]`` auto-select write-back

``GERDSENAI_LLM_API_KEY`` is intentionally NOT covered here — its behavior is
unchanged and already tested in tests/test_bridge_auth.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gerdsenai_cli.config.manager import ConfigManager
from gerdsenai_cli.main import GerdsenAICLI

ENV_CONFIG = "GERDSENAI_CONFIG"
ENV_URL = "GERDSENAI_LLM_SERVER_URL"
ENV_MODEL = "GERDSENAI_MODEL"


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch, tmp_path):
    """Isolate HOME and clear the override env vars regardless of harness env."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in (ENV_CONFIG, ENV_URL, ENV_MODEL):
        monkeypatch.delenv(var, raising=False)


def _write_config(path: Path, **fields: Any) -> Path:
    """Write a minimal valid config file with the given Settings fields."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fields), "utf-8")
    return path


# ---------------------------------------------------------------------------
# GERDSENAI_CONFIG — config file path selection
# ---------------------------------------------------------------------------


def test_gerdsenai_config_env_sets_config_path(monkeypatch, tmp_path):
    """GERDSENAI_CONFIG picks the config file when no --config flag is given."""
    custom = tmp_path / "elsewhere" / "custom.json"
    monkeypatch.setenv(ENV_CONFIG, str(custom))

    manager = ConfigManager()

    assert manager.config_file == custom


def test_explicit_config_path_wins_over_env(monkeypatch, tmp_path):
    """--config (explicit config_path) beats GERDSENAI_CONFIG."""
    explicit = tmp_path / "explicit.json"
    monkeypatch.setenv(ENV_CONFIG, str(tmp_path / "ignored.json"))

    manager = ConfigManager(str(explicit))

    assert manager.config_file == explicit


def test_default_path_used_without_env(tmp_path):
    """Baseline guard: no flag, no env -> XDG-ish default under HOME."""
    manager = ConfigManager()

    expected = tmp_path / ".config" / "gerdsenai-cli" / "config.json"
    assert manager.config_file == expected


# ---------------------------------------------------------------------------
# GERDSENAI_LLM_SERVER_URL — env beats file, invalid env fails loudly
# ---------------------------------------------------------------------------


async def test_env_server_url_overrides_file(monkeypatch, tmp_path):
    """Env URL beats the file's llm_server_url, including derived components."""
    cfg = _write_config(
        tmp_path / "config.json", llm_server_url="http://filehost:1111"
    )
    monkeypatch.setenv(ENV_URL, "http://envhost:2222")

    settings = await ConfigManager(str(cfg)).load_settings()

    assert settings is not None
    assert settings.llm_server_url == "http://envhost:2222"
    assert settings.protocol == "http"
    assert settings.llm_host == "envhost"
    assert settings.llm_port == 2222


async def test_env_server_url_overrides_granular_file_fields(monkeypatch, tmp_path):
    """Edge case: env URL equal to the built-in default still beats a file that
    only sets granular protocol/llm_host/llm_port fields (the sync_url_components
    validator must not silently prefer the file's granular values)."""
    cfg = _write_config(
        tmp_path / "config.json",
        protocol="https",
        llm_host="filehost",
        llm_port=9999,
    )
    monkeypatch.setenv(ENV_URL, "http://localhost:11434")  # == model default

    settings = await ConfigManager(str(cfg)).load_settings()

    assert settings is not None
    assert settings.llm_server_url == "http://localhost:11434"
    assert settings.protocol == "http"
    assert settings.llm_host == "localhost"
    assert settings.llm_port == 11434


@pytest.mark.parametrize(
    "bad_url",
    [
        "not-a-url",  # no scheme/host/port at all
        "http://host-no-port",  # missing explicit port
        "ftp://h:1",  # unsupported scheme
    ],
)
async def test_invalid_env_server_url_fails_loudly(monkeypatch, tmp_path, bad_url):
    """A malformed env URL raises ValueError naming the env var — it must never
    be swallowed into a silent localhost-default fallback."""
    cfg = _write_config(
        tmp_path / "config.json", llm_server_url="http://filehost:1111"
    )
    monkeypatch.setenv(ENV_URL, bad_url)

    with pytest.raises(ValueError, match="GERDSENAI_LLM_SERVER_URL"):
        await ConfigManager(str(cfg)).load_settings()


# ---------------------------------------------------------------------------
# GERDSENAI_MODEL — env beats file / fills empty model
# ---------------------------------------------------------------------------


async def test_env_model_overrides_file(monkeypatch, tmp_path):
    cfg = _write_config(tmp_path / "config.json", current_model="file-model")
    monkeypatch.setenv(ENV_MODEL, "env-model")

    settings = await ConfigManager(str(cfg)).load_settings()

    assert settings is not None
    assert settings.current_model == "env-model"


async def test_env_model_fills_empty_file_model(monkeypatch, tmp_path):
    """File without a model + env set -> env value (this is what makes
    initialize() skip the models[0] auto-select write-back)."""
    cfg = _write_config(
        tmp_path / "config.json", llm_server_url="http://filehost:1111"
    )
    monkeypatch.setenv(ENV_MODEL, "env-model")

    settings = await ConfigManager(str(cfg)).load_settings()

    assert settings is not None
    assert settings.current_model == "env-model"


# ---------------------------------------------------------------------------
# Sync path (slash commands) must agree with the async loader
# ---------------------------------------------------------------------------


def test_get_settings_sync_applies_env_overrides(monkeypatch, tmp_path):
    cfg = _write_config(
        tmp_path / "config.json",
        llm_server_url="http://filehost:1111",
        current_model="file-model",
    )
    monkeypatch.setenv(ENV_URL, "http://envhost:2222")
    monkeypatch.setenv(ENV_MODEL, "env-model")

    settings = ConfigManager(str(cfg)).get_settings()

    assert settings.llm_server_url == "http://envhost:2222"
    assert settings.llm_host == "envhost"
    assert settings.llm_port == 2222
    assert settings.current_model == "env-model"


def test_get_settings_sync_invalid_env_url_raises(monkeypatch, tmp_path):
    cfg = _write_config(
        tmp_path / "config.json", llm_server_url="http://filehost:1111"
    )
    monkeypatch.setenv(ENV_URL, "http://host-no-port")

    with pytest.raises(ValueError, match="GERDSENAI_LLM_SERVER_URL"):
        ConfigManager(str(cfg)).get_settings()


# ---------------------------------------------------------------------------
# Headless bootstrap: no config file + env URL -> initialize() proceeds
# ---------------------------------------------------------------------------


class _FakeModel:
    id = "first-listed-model"


class _FakeLLMClient:
    def __init__(self, settings):
        self.settings = settings

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def connect(self) -> bool:
        return True

    async def list_models(self):
        return [_FakeModel()]


class _FakeAgent:
    def __init__(self, llm_client, settings):
        self.llm_client = llm_client
        self.settings = settings
        self.context_manager = None

    async def initialize(self) -> bool:
        return True

    async def cleanup(self) -> None:
        return None


async def test_headless_bootstrap_with_env_url_no_config_file(monkeypatch, tmp_path):
    """No config file anywhere + GERDSENAI_LLM_SERVER_URL set -> headless
    initialize() succeeds with env-derived settings, env model is used, and the
    models[0] auto-select write-back is skipped (nothing persisted)."""
    monkeypatch.setenv(ENV_URL, "http://envhost:2222")
    monkeypatch.setenv(ENV_MODEL, "env-model")
    monkeypatch.setattr("gerdsenai_cli.main.LLMClient", _FakeLLMClient)
    monkeypatch.setattr("gerdsenai_cli.main.Agent", _FakeAgent)

    cli = GerdsenAICLI(config_path=None, interactive=False)

    saved: list[Any] = []

    async def _spy_save(settings) -> bool:
        saved.append(settings)
        return True

    monkeypatch.setattr(cli.config_manager, "save_settings", _spy_save)

    assert await cli.initialize() is True
    assert cli.settings is not None
    assert cli.settings.llm_server_url == "http://envhost:2222"
    assert cli.settings.current_model == "env-model"
    assert saved == []  # env model set -> no auto-select write-back


async def test_headless_no_config_no_env_errors_and_mentions_env_var(
    monkeypatch, tmp_path
):
    """Without a config file or env URL, headless init still fails fast — and
    the error now tells the user about GERDSENAI_LLM_SERVER_URL."""
    errors: list[str] = []
    monkeypatch.setattr(
        "gerdsenai_cli.main.show_error", lambda msg, *a, **kw: errors.append(msg)
    )

    cli = GerdsenAICLI(config_path=None, interactive=False)

    assert await cli.initialize() is False
    assert errors, "expected an error message"
    assert "GERDSENAI_LLM_SERVER_URL" in errors[0]


# ---------------------------------------------------------------------------
# Backward compatibility: no env vars -> file settings untouched
# ---------------------------------------------------------------------------


async def test_no_env_leaves_file_settings_untouched(tmp_path):
    cfg = _write_config(
        tmp_path / "config.json",
        llm_server_url="http://filehost:1111",
        current_model="file-model",
    )

    settings = await ConfigManager(str(cfg)).load_settings()

    assert settings is not None
    assert settings.llm_server_url == "http://filehost:1111"
    assert settings.llm_host == "filehost"
    assert settings.llm_port == 1111
    assert settings.current_model == "file-model"
