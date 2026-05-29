import asyncio
import os

from langchain_azure_ai.agents.hosting import ResponsesHostServer
from dem333.agent import build_agent


def _app_insights_connection_string() -> str | None:
    return (
        os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        or os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
        or os.getenv("DEM333_APPLICATIONINSIGHTS_CONNECTION_STRING")
    )


async def main() -> None:
    agent = await build_agent()

    host = ResponsesHostServer(
        graph=agent,
        applicationinsights_connection_string=_app_insights_connection_string(),
    )
    await host.run_async(port=int(os.getenv("PORT", "8088")))


if __name__ == "__main__":
    asyncio.run(main())