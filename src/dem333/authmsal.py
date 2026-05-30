import base64
import binascii
import os
import sys
from pathlib import Path

import msal


def _truthy(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _cache_file_path() -> Path:
    """Return token cache location, allowing override via env var."""
    cache_override = os.getenv("DEM333_MSAL_CACHE_PATH")
    if cache_override:
        return Path(cache_override).expanduser().resolve()

    return Path.home() / ".dem333" / "msal_token_cache.json"


def _serialized_cache_from_env() -> str | None:
    cache_json = os.getenv("DEM333_MSAL_CACHE_JSON")
    if cache_json:
        return cache_json

    cache_b64 = os.getenv("DEM333_MSAL_CACHE_B64")
    if not cache_b64:
        return None

    try:
        return base64.b64decode(cache_b64, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise RuntimeError(
            "DEM333_MSAL_CACHE_B64 is not valid base64-encoded UTF-8."
        ) from exc


def _env_cache_configured() -> bool:
    return bool(
        os.getenv("DEM333_MSAL_CACHE_JSON") or os.getenv("DEM333_MSAL_CACHE_B64")
    )


def _load_token_cache(cache_path: Path) -> msal.SerializableTokenCache:
    """Load existing MSAL cache from disk if present."""
    token_cache = msal.SerializableTokenCache()
    serialized_cache = _serialized_cache_from_env()
    if serialized_cache:
        token_cache.deserialize(serialized_cache)
        return token_cache

    if cache_path.exists():
        token_cache.deserialize(cache_path.read_text(encoding="utf-8"))
    return token_cache


def _save_token_cache(token_cache: msal.SerializableTokenCache, cache_path: Path) -> None:
    """Persist MSAL cache to disk only when changed."""
    if not token_cache.has_state_changed:
        return
    if _truthy(os.getenv("DEM333_DISABLE_CACHE_WRITE")):
        return
    if _env_cache_configured() and not _truthy(os.getenv("DEM333_SAVE_ENV_CACHE")):
        return

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = token_cache.serialize()
    cache_path.write_text(serialized, encoding="utf-8")

    # Restrict cache file permissions to current user on POSIX systems.
    try:
        cache_path.chmod(0o600)
    except OSError:
        pass


def _interactive_auth_enabled() -> bool:
    if _truthy(os.getenv("DEM333_DISABLE_INTERACTIVE_AUTH")):
        return False
    if _truthy(os.getenv("DEM333_ENABLE_INTERACTIVE_AUTH")):
        return True
    return sys.stdin.isatty()


def acquire_user_access_token(client_id: str, tenant_id: str, scope: str) -> str:
    """Acquire user delegated token via MSAL with persistent local cache."""
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    cache_path = _cache_file_path()
    token_cache = _load_token_cache(cache_path)

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
        token_cache=token_cache,
    )

    token_result = None
    accounts = app.get_accounts()
    if accounts:
        token_result = app.acquire_token_silent(scopes=[scope], account=accounts[0])

    if not token_result:
        if not _interactive_auth_enabled():
            raise RuntimeError(
                "Authentication failed: no usable MSAL token cache was available and "
                "interactive authentication is disabled. Sign in locally once to create "
                "the cache, then provide DEM333_MSAL_CACHE_B64 or DEM333_MSAL_CACHE_JSON "
                "as a secret runtime environment variable for hosted deployments."
            )
        token_result = app.acquire_token_interactive(scopes=[scope], prompt="select_account")

    _save_token_cache(token_cache, cache_path)

    access_token = token_result.get("access_token") if token_result else None
    if access_token:
        return access_token

    error = (token_result or {}).get("error", "unknown_error")
    description = (token_result or {}).get("error_description", "No details provided")

    if "AADSTS7000218" in description:
        raise RuntimeError(
            "Authentication failed: AADSTS7000218. "
            "This app registration is being treated as a confidential client. "
            "For MSAL interactive user flow (PublicClientApplication), in Entra set "
            "Authentication -> Advanced settings -> Allow public client flows = Yes, "
            "and keep a Mobile/Desktop redirect URI such as http://localhost."
        )

    raise RuntimeError(f"Authentication failed: {error}: {description}")
