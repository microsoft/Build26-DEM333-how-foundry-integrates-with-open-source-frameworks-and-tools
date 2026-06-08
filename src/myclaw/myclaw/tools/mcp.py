"""Generic configuration helpers shared by the agent's MCP server tools."""

from langchain.tools import BaseTool


def _format_mcp_tool_error(error: Exception) -> str:
    """Turn a raised tool error into a recoverable message the agent can act on."""
    first_line = str(error).splitlines()[0] if str(error) else type(error).__name__
    return (
        "The tool rejected that request. Retry once with corrected arguments and a "
        "smaller page size if the request returns a list. "
        f"Tool error: {first_line}"
    )


def configure_mcp_tool_error_handling(tools: list[BaseTool]) -> list[BaseTool]:
    """Configure MCP tools to surface recoverable tool errors back to the agent."""

    for tool in tools:
        tool.handle_tool_error = _format_mcp_tool_error
    return tools
