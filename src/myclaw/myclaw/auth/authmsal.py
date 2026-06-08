import base64
import binascii
import json
import os
import sys
from collections.abc import Generator
from pathlib import Path
import time
from typing import Any

import httpx
import msal

def _audience_matches(audience: Any, target_resource_id: str, target_app_id: str) -> bool:
    expected = {target_resource_id.rstrip("/"), target_app_id}
    if isinstance(audience, str):
        return audience.rstrip("/") in expected
    if isinstance(audience, list):
        return any(
            isinstance(value, str) and value.rstrip("/") in expected
            for value in audience
        )
    return False


def _validate_access_token(token: str, target_resource_id: str, target_app_id: str) -> None:
    claims = decode_jwt_payload(token)
    if not claims:
        # Opaque/non-JWT token: skip claim checks and let the server reject it if invalid.
        return

    if not _audience_matches(claims.get("aud"), target_resource_id, target_app_id):
        raise RuntimeError(f"Token must be an access token for {target_resource_id}.")

    expires_at = claims.get("exp")
    if isinstance(expires_at, int) and expires_at <= int(time.time()) + 60:
        raise RuntimeError("Token is expired or expires within the next minute.")


def _direct_access_token(environ: str, resource_id: str, app_id: str) -> str | None:
    token = os.getenv(environ)
    if token:
        _validate_access_token(token, resource_id, app_id)
        return token
    return None

def _acquire_access_token(scope: str, tenant_id: str, client_id: str | None, resource_id: str, app_id: str, environ: str) -> str:
    """Resolve a Work IQ token: prefer a direct env token, else MSAL cache/interactive.

    The client ID is only required when no direct token is present, so callers
    using ``WORK_IQ_ACCESS_TOKEN`` never need to configure one.
    """
    direct_token = _direct_access_token(environ, resource_id, app_id)
    if direct_token:
        return direct_token

    return acquire_user_access_token(
        client_id=client_id,
        tenant_id=tenant_id,
        scope=scope,
        environ=environ
    )

class BearerTokenAuthWithCache(httpx.Auth):
    """Attach a bearer token to each outgoing HTTP request, reusing a cached
    token until it is close to expiry.

    Implemented as an ``httpx.Auth`` so the credential is resolved lazily and
    refreshed automatically. The resolved token is held in memory and reused
    across requests, so repeated calls do not trigger a fresh MSAL sign-in or
    cache lookup until the current token is about to expire.
    """

    # Refresh a little before the real expiry to avoid sending a token that
    # lapses mid-flight.
    _EXPIRY_SKEW_SECONDS: int = 60

    def __init__(self, scope: str, tenant_id: str, client_id: str | None, resource_id: str, app_id: str, environ: str = "MSAL_ACCESS_TOKEN") -> None:
        self._scope = scope
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._resource_id = resource_id
        self._app_id = app_id
        self._environ = environ
        self._cached_token: str | None = None
        self._cached_expiry: float = 0.0

    def has_usable_credentials(self) -> bool:
        """Return True when the auth can resolve a token without a sign-in error.

        A token is obtainable when either a client ID is configured (enabling the
        MSAL cache/interactive flow) or a valid direct token is present in the
        configured environment variable.
        """
        if self._client_id:
            return True
        return _direct_access_token(self._environ, self._resource_id, self._app_id) is not None

    def _acquire_token(self) -> str:
        return _acquire_access_token(
            scope=self._scope,
            tenant_id=self._tenant_id,
            client_id=self._client_id,
            resource_id=self._resource_id,
            app_id=self._app_id,
            environ=self._environ,
        )

    def _get_token(self) -> str:
        now = time.time()
        if self._cached_token and now < self._cached_expiry - self._EXPIRY_SKEW_SECONDS:
            return self._cached_token

        token = self._acquire_token()
        self._cached_token = token
        self._cached_expiry = _token_expiry(token)
        return token

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self._get_token()}"
        yield request


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Decode the unverified payload (claims) of a JWT access token.

    Returns the claims dict, or None when the token has no decodable payload.
    Raises RuntimeError if a payload is present but is not valid base64url JSON.
    """
    parts = token.split(".")
    if len(parts) < 2:
        return None

    padded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = base64.urlsafe_b64decode(padded_payload.encode("ascii"))
        claims = json.loads(payload.decode("utf-8"))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Access token is not a valid JWT.") from exc

    return claims if isinstance(claims, dict) else None


def _token_expiry(token: str) -> float:
    """Return a token's expiry as a POSIX timestamp.

    JWT access tokens expose their expiry via the ``exp`` claim. Opaque tokens
    (and JWTs without an ``exp``) return ``0.0`` so the caller treats them as
    already expired and re-resolves them on the next request.
    """
    claims = decode_jwt_payload(token)
    if claims:
        expires_at = claims.get("exp")
        if isinstance(expires_at, (int, float)):
            return float(expires_at)
    return 0.0


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
    if _truthy(os.getenv("WORK_IQ_DISABLE_INTERACTIVE_AUTH")):
        return False
    if _truthy(os.getenv("WORK_IQ_ENABLE_INTERACTIVE_AUTH")):
        return True
    return sys.stdin.isatty()


def acquire_user_access_token(client_id: str | None, tenant_id: str, scope: str, environ: str) -> str:
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
