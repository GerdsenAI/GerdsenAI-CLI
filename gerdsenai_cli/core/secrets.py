"""Secret storage for provider API keys.

Keys are read from (in order): the OS keyring (macOS Keychain / Linux Secret
Service via the optional ``keyring`` package), then an environment variable.
Secrets are **never** written to ``config.json``. When ``keyring`` is not
installed, the environment variable is the only source and ``set_secret`` is a
no-op that reports failure.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

SERVICE_NAME = "gerdsenai-cli"

# Map a provider/secret name to its environment-variable fallback.
_ENV_FALLBACKS = {
    "anthropic": "ANTHROPIC_API_KEY",
}


def _keyring():  # type: ignore[no-untyped-def]
    """Return the keyring module if available, else None."""
    try:
        import keyring

        return keyring
    except Exception:
        return None


def keyring_available() -> bool:
    """True if the optional keyring backend is importable."""
    return _keyring() is not None


def get_secret(name: str) -> str | None:
    """Return the secret for ``name`` from the keyring, then the env fallback."""
    kr = _keyring()
    if kr is not None:
        try:
            value = kr.get_password(SERVICE_NAME, name)
            if value:
                return str(value)
        except Exception as e:
            logger.debug(f"keyring lookup failed for {name}: {e}")

    env_var = _ENV_FALLBACKS.get(name)
    if env_var:
        return os.environ.get(env_var)
    return None


def set_secret(name: str, value: str) -> bool:
    """Store a secret in the OS keyring. Returns False if keyring is absent."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        kr.set_password(SERVICE_NAME, name, value)
        return True
    except Exception as e:
        logger.debug(f"keyring store failed for {name}: {e}")
        return False


def delete_secret(name: str) -> bool:
    """Remove a secret from the OS keyring. Returns True if something was removed."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        kr.delete_password(SERVICE_NAME, name)
        return True
    except Exception:
        return False


def secret_source(name: str) -> str | None:
    """Where the secret currently resolves from: 'keyring', 'env', or None."""
    kr = _keyring()
    if kr is not None:
        try:
            if kr.get_password(SERVICE_NAME, name):
                return "keyring"
        except Exception:
            pass
    env_var = _ENV_FALLBACKS.get(name)
    if env_var and os.environ.get(env_var):
        return "env"
    return None
