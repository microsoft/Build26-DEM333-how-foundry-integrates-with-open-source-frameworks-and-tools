import os
from typing import Any

from dem333.authmsal import acquire_user_access_token


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


# Work IQ tenant used in the Mail MCP server path.
WORK_IQ_TENANT_ID: str = _require_env("AZURE_TENANT_ID")

# Entra app registration used for interactive delegated sign-in to Work IQ.
WORK_IQ_CLIENT_ID: str = _require_env("AZURE_CLIENT_ID")

# OAuth scope required by the Work IQ Mail MCP server.
WORK_IQ_MAIL_SCOPE: str = "https://agent365.svc.cloud.microsoft/.default"

WORK_IQ_MAIL_SERVER_URL: str = (
    f"https://agent365.svc.cloud.microsoft/agents/tenants/{WORK_IQ_TENANT_ID}/servers/mcp_MailTools"
)


def build_work_iq_mail_server_config(access_token: str) -> dict[str, Any]:
    """Build MCP server configuration for Work IQ Mail tools."""
    return {
        "url": WORK_IQ_MAIL_SERVER_URL,
        "transport": "streamable_http",
        "headers": {"Authorization": f"Bearer {access_token}"},
    }


def build_work_iq_mail_connection() -> dict[str, Any]:
    """Build authenticated MCP connection config for Work IQ Mail tools."""
    token = acquire_user_access_token(
        client_id=WORK_IQ_CLIENT_ID,
        tenant_id=WORK_IQ_TENANT_ID,
        scope=WORK_IQ_MAIL_SCOPE,
    )
    return build_work_iq_mail_server_config(access_token=token)
