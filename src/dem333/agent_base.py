"""Minimal teaching version of the agent.

This file shows the smallest useful shape of the DEM333 agent: it creates a
chat model, applies the shared system prompt, and enables checkpointed memory
before returning a `deepagents` agent instance.

Compared with the later tutorial steps, this version does not register MCP
tools, does not expose local skills through the backend, and does not add the
browser tool that appears in the final `agent.py`.
"""

from dem333.prompt import SYSTEM_PROMPT
from deepagents import create_deep_agent

from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver


checkpointer = MemorySaver()

async def build_agent():
    """Build a deep learning agent with the provided MCP tools."""
    model = init_chat_model("openai:gpt-5.2")
    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

