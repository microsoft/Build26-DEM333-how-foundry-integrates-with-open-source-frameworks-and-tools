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
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser(
        "search", help="Search configured A2A agents and print matching entries."
    )
    search_parser.add_argument("query", help="Search query for the agent directory.")

    call_parser = subparsers.add_parser(
        "call", help="Invoke an A2A agent once and print the response."
    )
    call_parser.add_argument(
        "--agent-id",
        default=None,
        help="Configured A2A agent id to call (default: first configured agent).",
    )
    call_parser.add_argument(
        "--message",
        required=True,
        help="Message to send to the A2A agent.",
    )

    serve_parser = subparsers.add_parser(
        "serve", help="Start the MCP server (default when no command is given)."
    )
    serve_parser.add_argument(
        "--protocol",
        choices=("stdio", "http", "sse"),
        default="stdio",
        help="Transport for the MCP server (default: stdio).",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for the http/sse transports (default: 127.0.0.1).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for the http/sse transports (default: 8000).",
    )

    args = parser.parse_args()

    if args.command == "search":
        asyncio.run(_direct_search(args.query))
        return

    if args.command == "call":
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

    protocol = getattr(args, "protocol", "stdio")
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)
    run(protocol=protocol, host=host, port=port)


if __name__ == "__main__":
    main()
