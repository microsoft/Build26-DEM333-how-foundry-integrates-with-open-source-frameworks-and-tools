from typing import Any

from myclaw.prompts.prompt import SYSTEM_PROMPT
from myclaw.tools.work_iq import build_work_iq_mail_connection
from myclaw.tools.mcp import configure_mcp_tool_error_handling
from myclaw.tools.browser import playwright_cli
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

from langchain.tools import BaseTool
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

SKILL_SOURCES = ["/skills/"]


async def get_tools() -> list[BaseTool]:
    """Get the list of available tools."""
    
    mcp_client = get_mcp_servers()
    mcp_tools = await mcp_client.get_tools()
    mcp_tools = configure_mcp_tool_error_handling(mcp_tools)

    return mcp_tools + [playwright_cli]


def get_mcp_servers() -> MultiServerMCPClient:
    """Gets the MCP servers to be used by the agent."""
    
    connections: dict[str, Any] = {
        "mail": build_work_iq_mail_connection()
    }
    return MultiServerMCPClient(connections)


async def build_agent() -> CompiledStateGraph:
    """Build a deep learning agent with the provided MCP tools."""
    
    model = init_chat_model("openai:gpt-5.2")
    tools = await get_tools()
    checkpointer = MemorySaver()

    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/skills/": FilesystemBackend(root_dir="myclaw/skills", virtual_mode=True),
        },
    )
    
    return create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        skills=SKILL_SOURCES,
        checkpointer=checkpointer,
        backend=backend,
    )
