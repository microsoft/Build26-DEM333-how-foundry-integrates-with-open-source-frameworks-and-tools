"""Authenticated MCP connection and tool config for the Microsoft 365 Work IQ Mail server.

Resolves a delegated Work IQ access token (direct env token, MSAL cache, or
interactive sign-in), attaches it as a bearer credential on every MCP HTTP
request, and surfaces recoverable mail-tool errors back to the agent.
"""

from typing import Any

from myclaw.auth.authmsal import BearerTokenAuthWithCache
from myclaw.utils import first_env


# OAuth scope required by the Work IQ Mail MCP server.
WORK_IQ_MAIL_SCOPE: str = "https://agent365.svc.cloud.microsoft/.default"
WORK_IQ_RESOURCE: str = "https://agent365.svc.cloud.microsoft"
WORK_IQ_RESOURCE_APP_ID: str = "ea9ffc3e-8a23-4a7d-836d-234d7c7565c1"

def build_work_iq_mail_connection() -> dict[str, Any]:
    """Build authenticated MCP connection config for Work IQ Mail tools."""

    tenant_id = first_env("WORK_IQ_TENANT_ID", "AZURE_TENANT_ID")
    if not tenant_id:
        raise RuntimeError(
            "Missing Work IQ tenant ID. Set WORK_IQ_TENANT_ID for Work IQ Mail. "
            "AZURE_TENANT_ID remains supported as a local backwards-compatible fallback."
        )

    # A client ID is only needed when falling back to MSAL cache/interactive auth.
    client_id = first_env("WORK_IQ_CLIENT_ID", "AZURE_CLIENT_ID")

    auth = BearerTokenAuthWithCache(
        scope=WORK_IQ_MAIL_SCOPE,
        tenant_id=tenant_id,
        client_id=client_id,
        resource_id=WORK_IQ_RESOURCE,
        app_id=WORK_IQ_RESOURCE_APP_ID,
        environ="WORK_IQ_ACCESS_TOKEN",
    )
    if not auth.has_usable_credentials():
        raise RuntimeError(
            "Missing Work IQ client ID. Set WORK_IQ_CLIENT_ID for MSAL cache or "
            "interactive auth. Do not set AZURE_CLIENT_ID in hosted deployments unless it "
            "is the hosted agent managed identity client ID."
        )

    return {
        "url": f"{WORK_IQ_RESOURCE}/agents/tenants/{tenant_id}/servers/mcp_MailTools",
        "transport": "streamable_http",
        "auth": auth,
    }
