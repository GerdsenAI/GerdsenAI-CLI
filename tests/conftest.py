"""
Pytest configuration for GerdsenAI CLI tests.

Configures pytest-asyncio and other test settings.
"""
# cspell:ignore argparsing addinivalue addoption ollama lmstudio vllm huggingface autouse tiktoken

import os
from typing import Any

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.fixtures import FixtureRequest
from _pytest.monkeypatch import MonkeyPatch


# Configure pytest-asyncio
def pytest_configure(config: Config) -> None:
    """Configure pytest with asyncio settings."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )


def pytest_addoption(parser: Parser) -> None:
    """Add custom command-line options for LLM provider configuration."""
    parser.addoption(
        "--llm-provider",
        action="store",
        default=None,
        help="LLM provider to use (ollama, lmstudio, vllm, huggingface)",
    )
    parser.addoption(
        "--llm-host",
        action="store",
        default=None,
        help="LLM server host (default: localhost)",
    )
    parser.addoption(
        "--llm-port",
        action="store",
        type=int,
        default=None,
        help="LLM server port (provider-specific defaults)",
    )
    parser.addoption(
        "--llm-model",
        action="store",
        default=None,
        help="Model name to use for testing",
    )


@pytest.fixture(scope="session")
def llm_config(request: FixtureRequest) -> dict[str, Any]:
    """
    Create LLM configuration from CLI options or environment variables.

    Priority: CLI options > Environment variables > Provider defaults

    Returns:
        dict: Configuration with keys: provider, host, port, protocol, model, timeout
    """
    # Provider-specific defaults
    PROVIDER_DEFAULTS = {
        "ollama": {"port": 11434, "protocol": "http"},
        "lmstudio": {"port": 1234, "protocol": "http"},
        "vllm": {"port": 8000, "protocol": "http"},
        "huggingface": {"port": 8080, "protocol": "http"},
    }

    # Get provider (CLI > ENV > default)
    provider = (
        request.config.getoption("--llm-provider")
        or os.getenv("LLM_PROVIDER")
        or "ollama"
    ).lower()

    # Validate provider
    if provider not in PROVIDER_DEFAULTS:
        raise ValueError(
            f"Invalid provider '{provider}'. Must be one of: "
            f"{', '.join(PROVIDER_DEFAULTS.keys())}"
        )

    # Get host (CLI > ENV > default)
    host = (
        request.config.getoption("--llm-host")
        or os.getenv("LLM_HOST")
        or "localhost"
    )

    # Get port (CLI > ENV > provider default)
    llm_port_env = os.getenv("LLM_PORT")
    port = (
        request.config.getoption("--llm-port")
        or (int(llm_port_env) if llm_port_env else None)
        or PROVIDER_DEFAULTS[provider]["port"]
    )

    # Get protocol (ENV > provider default)
    protocol = (
        os.getenv("LLM_PROTOCOL")
        or PROVIDER_DEFAULTS[provider]["protocol"]
    )

    # Get model (CLI > ENV > empty string)
    model = (
        request.config.getoption("--llm-model")
        or os.getenv("LLM_MODEL")
        or ""
    )

    # Get timeout (ENV > default)
    timeout = float(os.getenv("LLM_TIMEOUT", "15.0"))

    config = {
        "provider": provider,
        "host": host,
        "port": port,
        "protocol": protocol,
        "model": model,
        "timeout": timeout,
    }

    print(f"\n[LLM Config] Provider: {provider}")
    print(f"[LLM Config] Host: {host}:{port}")
    print(f"[LLM Config] Protocol: {protocol}")
    print(f"[LLM Config] Model: {model or '(auto-detect)'}")
    print(f"[LLM Config] Timeout: {timeout}s")

    return config


@pytest.fixture(autouse=True)
def mock_tiktoken_download(monkeypatch: MonkeyPatch) -> None:
    """
    Mock tiktoken encoding downloads to avoid network calls in tests.

    This fixture automatically applies to all tests and prevents tiktoken
    from trying to download encoding files from the internet.
    """
    try:
        import tiktoken  # pyright: ignore[reportMissingImports]  # type: ignore[import-not-found]

        # Create a mock encoding that can encode/decode
        class MockEncoding:
            """Mock tiktoken encoding for testing."""

            def encode(self, text: str, disallowed_special: tuple[str, ...] = ()) -> list[int]:
                """Mock encode - returns ~4 chars per token."""
                if not text:
                    return []
                # Simple approximation: 4 characters per token
                return list(range(len(text) // 4 + 1))

            def decode(self, tokens: list[int]) -> str:
                """Mock decode."""
                return "test" * len(tokens)

        # Mock get_encoding to return our mock encoding
        def mock_get_encoding(encoding_name: str) -> MockEncoding:
            """Return mock encoding instead of downloading."""
            return MockEncoding()

        monkeypatch.setattr(tiktoken, "get_encoding", mock_get_encoding)

    except ImportError:
        # tiktoken not available, skip mocking
        pass
