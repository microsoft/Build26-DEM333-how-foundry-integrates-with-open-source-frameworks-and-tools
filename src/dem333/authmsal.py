import os
from pathlib import Path

import msal


def _cache_file_path() -> Path:
    """Return token cache location, allowing override via env var."""
    cache_override = os.getenv("DEM333_MSAL_CACHE_PATH")
    if cache_override:
        return Path(cache_override).expanduser().resolve()

    return Path.home() / ".dem333" / "msal_token_cache.json"


def _load_token_cache(cache_path: Path) -> msal.SerializableTokenCache:
    """Load existing MSAL cache from disk if present."""
    token_cache = msal.SerializableTokenCache()
    if cache_path.exists():
        token_cache.deserialize(cache_path.read_text(encoding="utf-8"))
    return token_cache


def _save_token_cache(token_cache: msal.SerializableTokenCache, cache_path: Path) -> None:
    """Persist MSAL cache to disk only when changed."""
    if not token_cache.has_state_changed:
        return

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = token_cache.serialize()
    cache_path.write_text(serialized, encoding="utf-8")

    # Restrict cache file permissions to current user on POSIX systems.
    try:
        cache_path.chmod(0o600)
    except OSError:
        pass


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
