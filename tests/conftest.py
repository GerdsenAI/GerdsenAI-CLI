"""
Pytest configuration for GerdsenAI CLI tests.

Configures pytest-asyncio and other test settings.
"""

import pytest
from unittest.mock import MagicMock


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio settings."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )


@pytest.fixture(autouse=True)
def mock_tiktoken_download(monkeypatch):
    """
    Mock tiktoken encoding downloads to avoid network calls in tests.

    This fixture automatically applies to all tests and prevents tiktoken
    from trying to download encoding files from the internet.
    """
    try:
        import tiktoken
        from tiktoken import Encoding

        # Create a mock encoding that can encode/decode
        class MockEncoding:
            """Mock tiktoken encoding for testing."""

            def encode(self, text, disallowed_special=()):
                """Mock encode - returns ~4 chars per token."""
                if not text:
                    return []
                # Simple approximation: 4 characters per token
                return list(range(len(text) // 4 + 1))

            def decode(self, tokens):
                """Mock decode."""
                return "test" * len(tokens)

        # Mock get_encoding to return our mock encoding
        original_get_encoding = tiktoken.get_encoding

        def mock_get_encoding(encoding_name):
            """Return mock encoding instead of downloading."""
            return MockEncoding()

        monkeypatch.setattr(tiktoken, "get_encoding", mock_get_encoding)

    except ImportError:
        # tiktoken not available, skip mocking
        pass
