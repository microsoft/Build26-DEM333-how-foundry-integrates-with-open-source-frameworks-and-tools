import asyncio

from langchain_azure_ai.agents.hosting import ResponsesHostServer
from dem333.agent import build_agent, get_mcp_client, get_tools

async def main() -> None:
    agent = await build_agent()

    host = ResponsesHostServer(graph=agent)
    await host.run_async(port=8088)


if __name__ == "__main__":
    asyncio.run(main())