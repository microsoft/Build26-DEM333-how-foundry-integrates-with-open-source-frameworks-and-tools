import argparse
import asyncio
import json
import sys

from .client import configure_local_tracing, flush_local_tracing, invoke_a2a_agent
from .registry import get_agent, load_agents, search_agents
from .server import run


async def _direct_call(agent_id: str, message: str) -> str:
    return await invoke_a2a_agent(get_agent(agent_id), message)


async def _direct_search(query: str) -> None:
    results = await search_agents(query)
    print(json.dumps(results, indent=2, ensure_ascii=False))


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

    run()


if __name__ == "__main__":
    main()
