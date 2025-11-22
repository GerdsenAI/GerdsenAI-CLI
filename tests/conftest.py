"""
Pytest configuration for GerdsenAI CLI tests.

Configures pytest-asyncio and other test settings.
"""



# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with asyncio settings."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
