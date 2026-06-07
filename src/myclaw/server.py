import asyncio
import os
from langchain_azure_ai.agents.hosting import ResponsesHostServer
from myclaw.agent import build_agent

async def main() -> None:
    graph = await build_agent()
    port = int(os.environ.get("PORT", "8088"))
    await ResponsesHostServer(graph).run_async(port=port)

if __name__ == "__main__":
    asyncio.run(main())