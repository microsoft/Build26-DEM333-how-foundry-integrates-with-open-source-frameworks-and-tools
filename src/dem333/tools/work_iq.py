import base64
import binascii
import json
import os
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx

from dem333.authmsal import acquire_user_access_token


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


# OAuth scope required by the Work IQ Mail MCP server.
WORK_IQ_MAIL_SCOPE: str = "https://agent365.svc.cloud.microsoft/.default"
WORK_IQ_RESOURCE: str = "https://agent365.svc.cloud.microsoft"
WORK_IQ_RESOURCE_APP_ID: str = "ea9ffc3e-8a23-4a7d-836d-234d7c7565c1"


class WorkIqBearerAuth(httpx.Auth):
    """Attach a fresh delegated Work IQ token to each MCP HTTP request."""

    def __init__(self, token_provider: Callable[[], str]) -> None:
        self._token_provider = token_provider

    def auth_flow(self, request: httpx.Request) -> Iterator[httpx.Request]:
        request.headers["Authorization"] = f"Bearer {self._token_provider()}"
        yield request


def _work_iq_mail_server_url(tenant_id: str) -> str:
    return f"{WORK_IQ_RESOURCE}/agents/tenants/{tenant_id}/servers/mcp_MailTools"


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None

    padded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = base64.urlsafe_b64decode(padded_payload.encode("ascii"))
        claims = json.loads(payload.decode("utf-8"))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("Work IQ access token is not a valid JWT.") from exc

    return claims if isinstance(claims, dict) else None


def _audience_matches(audience: Any) -> bool:
    expected = {WORK_IQ_RESOURCE.rstrip("/"), WORK_IQ_RESOURCE_APP_ID}
    if isinstance(audience, str):
        return audience.rstrip("/") in expected
    if isinstance(audience, list):
        return any(
            isinstance(value, str) and value.rstrip("/") in expected
            for value in audience
        )
    return False


def _validate_work_iq_access_token(token: str, env_name: str) -> None:
    claims = _decode_jwt_payload(token)
    if not claims:
        return

    if not _audience_matches(claims.get("aud")):
        raise RuntimeError(f"{env_name} must be an access token for {WORK_IQ_RESOURCE}.")

    expires_at = claims.get("exp")
    if isinstance(expires_at, int) and expires_at <= int(time.time()) + 60:
        raise RuntimeError(f"{env_name} is expired or expires within the next minute.")


def _direct_work_iq_access_token() -> str | None:
    for env_name in ("DEM333_WORK_IQ_ACCESS_TOKEN", "WORK_IQ_ACCESS_TOKEN"):
        token = os.getenv(env_name)
        if token:
            _validate_work_iq_access_token(token, env_name)
            return token
    return None


def _work_iq_client_id_required() -> str:
    value = _first_env("DEM333_WORK_IQ_CLIENT_ID", "WORK_IQ_CLIENT_ID", "AZURE_CLIENT_ID")
    if value:
        return value
    raise RuntimeError(
        "Missing Work IQ client ID. Set DEM333_WORK_IQ_CLIENT_ID for MSAL cache or "
        "interactive auth. Do not set AZURE_CLIENT_ID in hosted deployments unless it "
        "is the hosted agent managed identity client ID."
    )


def _acquire_work_iq_access_token(client_id: str | None, tenant_id: str) -> str:
    direct_token = _direct_work_iq_access_token()
    if direct_token:
        return direct_token

    if not client_id:
        client_id = _work_iq_client_id_required()

    return acquire_user_access_token(
        client_id=client_id,
        tenant_id=tenant_id,
        scope=WORK_IQ_MAIL_SCOPE,
    )


def build_work_iq_mail_server_config(tenant_id: str, auth: httpx.Auth) -> dict[str, Any]:
    """Build MCP server configuration for Work IQ Mail tools."""
    return {
        "url": _work_iq_mail_server_url(tenant_id),
        "transport": "streamable_http",
        "auth": auth,
    }


def build_work_iq_mail_connection() -> dict[str, Any]:
    """Build authenticated MCP connection config for Work IQ Mail tools."""
    tenant_id = _first_env("DEM333_WORK_IQ_TENANT_ID", "WORK_IQ_TENANT_ID", "AZURE_TENANT_ID")
    if not tenant_id:
        raise RuntimeError(
            "Missing Work IQ tenant ID. Set DEM333_WORK_IQ_TENANT_ID for Work IQ Mail. "
            "AZURE_TENANT_ID remains supported as a local backwards-compatible fallback."
        )
    client_id = _first_env("DEM333_WORK_IQ_CLIENT_ID", "WORK_IQ_CLIENT_ID", "AZURE_CLIENT_ID")
    auth = WorkIqBearerAuth(
        lambda: _acquire_work_iq_access_token(client_id=client_id, tenant_id=tenant_id)
    )
    return build_work_iq_mail_server_config(tenant_id=tenant_id, auth=auth)


def _format_work_iq_tool_error(error: Exception) -> str:
    first_line = str(error).splitlines()[0] if str(error) else type(error).__name__
    return (
        "The mail tool rejected that request. Retry once with a smaller page and valid "
        "tool arguments. For SearchMessagesQueryParameters, queryParameters must start "
        "with '?' and include each OData parameter separately, for example "
        "'?$select=id,subject,from,receivedDateTime&$top=5'. "
        f"Tool error: {first_line}"
    )


def configure_work_iq(tools: list[Any]) -> list[Any]:
    """Return MCP tools configured to surface recoverable tool errors to the agent."""
    for tool in tools:
        tool.handle_tool_error = _format_work_iq_tool_error
    return tools
