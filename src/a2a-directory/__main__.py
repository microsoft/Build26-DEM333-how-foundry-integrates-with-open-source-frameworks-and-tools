import argparse
import asyncio
import sys
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from a2a_directory.client import configure_local_tracing, flush_local_tracing, get_agent_card, invoke_a2a_agent
from .registry import A2AAgent, find_agent, load_agents


mcp = FastMCP("a2a-directory")


def _agent_matches(agent: A2AAgent, query: str, card_summary: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            agent.id,
            agent.name,
            agent.description,
            " ".join(agent.tags),
            card_summary,
        ]
    ).lower()
    return all(term in haystack for term in query.lower().split())


def _card_summary(agent_card: Any) -> dict[str, Any]:
    skills = []
    for skill in getattr(agent_card, "skills", []) or []:
        skills.append(
            {
                "id": getattr(skill, "id", None),
                "name": getattr(skill, "name", None),
                "description": getattr(skill, "description", None),
                "tags": list(getattr(skill, "tags", []) or []),
            }
        )
    return {
        "name": getattr(agent_card, "name", None),
        "description": getattr(agent_card, "description", None),
        "skills": skills,
    }


@mcp.tool()
async def search_agent(query: str = "") -> list[dict[str, Any]]:
    """Search the configured A2A agent directory.

    Returns allowlisted agent IDs that can be passed to call_agent_a2a.
    """

    results: list[dict[str, Any]] = []
    for agent in load_agents():
        card: dict[str, Any] | None = None
        card_text = ""
        try:
            card = _card_summary(await get_agent_card(agent))
            card_text = str(card)
        except Exception as exc:
            card = {"error": f"agent card lookup failed: {exc}"}

        if _agent_matches(agent, query, card_text):
            results.append(
                {
                    "agent_id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "tags": list(agent.tags),
                    "agent_card": card,
                }
            )
    return results


@mcp.tool()
async def call_agent_a2a(agent_id: str, message: str, ctx: Context) -> str:
    """Call one configured A2A agent by ID. Use search_agent first."""

    agent = find_agent(agent_id)
    return await invoke_a2a_agent(agent, message, ctx)


async def _direct_call(agent_id: str, message: str) -> str:
    return await invoke_a2a_agent(find_agent(agent_id), message)


async def _direct_search(query: str) -> None:
    for result in await search_agent(query):
        print(result)


def main() -> None:
    configure_local_tracing()

    parser = argparse.ArgumentParser(
        description="Generic A2A directory MCP server for Copilot CLI."
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help="Search configured A2A agents and print matching entries.",
    )
    parser.add_argument(
        "--agent-id",
        default=None,
        help="Configured A2A agent id to call when --message is provided.",
    )
    parser.add_argument(
        "--message",
        help="Invoke an A2A agent once and print the response instead of starting MCP.",
    )
    args = parser.parse_args()

    if args.search is not None:
        asyncio.run(_direct_search(args.search))
        return

    if args.message:
        agents = load_agents()
        agent_id = args.agent_id or agents[0].id
        try:
            print(asyncio.run(_direct_call(agent_id, args.message)))
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
        finally:
            flush_local_tracing()
        return

    mcp.run()


if __name__ == "__main__":
    main()
