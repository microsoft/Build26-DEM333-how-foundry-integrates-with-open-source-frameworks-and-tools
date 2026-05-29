import argparse
import asyncio
import logging
import os
import subprocess
from collections.abc import Iterable
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from mcp.server.fastmcp import FastMCP


DEFAULT_AGENT_CARD_PATH = "agentCard/v0.3"
DEFAULT_TOKEN_RESOURCE = "https://ai.azure.com"
DEFAULT_TIMEOUT_SECONDS = 180.0

logging.getLogger("a2a").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value


def _get_foundry_token() -> str:
    token = os.getenv("FOUNDRY_A2A_TOKEN")
    if token:
        return token

    resource = os.getenv("FOUNDRY_A2A_TOKEN_RESOURCE", DEFAULT_TOKEN_RESOURCE)
    try:
        result = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                resource,
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        raise RuntimeError(
            f"Azure CLI failed to get a Foundry access token: {stderr or exc}"
        ) from exc
    token = result.stdout.strip()
    if not token:
        raise RuntimeError("Azure CLI returned an empty Foundry access token")
    return token


def _safe_join(items: Iterable[str]) -> str:
    return "\n".join(dict.fromkeys(item.strip() for item in items if item.strip()))


def _collect_text(value: Any, output: list[str]) -> None:
    if value is None:
        return

    text = getattr(value, "text", None)
    if isinstance(text, str) and text:
        output.append(text)

    for attr in ("artifacts", "parts"):
        for item in getattr(value, attr, []) or []:
            _collect_text(item, output)


def _extract_response_text(response: Any) -> str:
    text_parts: list[str] = []
    for candidate in (
        response,
        getattr(response, "task", None),
        getattr(response, "message", None),
        getattr(response, "result", None),
    ):
        _collect_text(candidate, text_parts)

    return _safe_join(text_parts) or str(response)


async def invoke_foundry_a2a(message: str) -> str:
    """Invoke the DEM333 hosted agent through its Foundry A2A endpoint."""
    base_url = _required_env("FOUNDRY_A2A_URL").rstrip("/")
    agent_card_path = os.getenv("FOUNDRY_A2A_AGENT_CARD_PATH", DEFAULT_AGENT_CARD_PATH)
    token = _get_foundry_token()

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(float(os.getenv("FOUNDRY_A2A_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))),
    ) as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            agent_card_path=agent_card_path,
        )
        agent_card = await resolver.get_agent_card()
        client = await create_client(
            agent=agent_card,
            client_config=ClientConfig(streaming=False, httpx_client=httpx_client),
        )
        try:
            request = SendMessageRequest(
                message=new_text_message(message, role=Role.ROLE_USER)
            )
            responses = [
                _extract_response_text(response)
                async for response in client.send_message(request)
            ]
        finally:
            await client.close()

    return _safe_join(responses)


mcp = FastMCP("dem333-a2a")


@mcp.tool()
async def ask_dem333_agent(message: str) -> str:
    """Ask the DEM333 Foundry hosted agent through its A2A endpoint."""
    return await invoke_foundry_a2a(message)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copilot CLI MCP bridge for the DEM333 Foundry A2A endpoint."
    )
    parser.add_argument(
        "--message",
        help="Invoke the A2A endpoint once and print the response instead of starting MCP.",
    )
    args = parser.parse_args()

    if args.message:
        print(asyncio.run(invoke_foundry_a2a(args.message)))
        return

    mcp.run()


if __name__ == "__main__":
    main()
