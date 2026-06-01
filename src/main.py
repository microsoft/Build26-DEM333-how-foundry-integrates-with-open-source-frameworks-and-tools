import argparse
import asyncio
import secrets
import warnings

# Suppress preview/beta warnings before importing modules that trigger them at import time.
from langchain_core._api import LangChainBetaWarning
from langchain_azure_ai._api.base import ExperimentalWarning

warnings.filterwarnings("ignore", category=LangChainBetaWarning)
warnings.filterwarnings("ignore", category=ExperimentalWarning)

from dem333.utils import inspect_loaded_skills
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text
from typing import Any, Awaitable, Callable


EXIT_COMMANDS = {"exit", "quit", ":q"}
HELP_COMMANDS = {"help", "/help", "?"}
RESET_COMMANDS = {"clear", "/clear", "/reset"}
console = Console()


def _new_thread_id() -> str:
    """Create a new checkpointer thread ID for the current chat session."""
    return str(secrets.randbelow(1_000_000_000))


def _extract_text(result: object) -> str:
    """Extract assistant text from agent output across common result shapes."""
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        messages = result.get("messages")
        if isinstance(messages, list) and messages:
            last_message = messages[-1]

            content = getattr(last_message, "content", None)
            if content is None and isinstance(last_message, dict):
                content = last_message.get("content")

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                if parts:
                    return "\n".join(parts)

        for key in ("output", "response", "text"):
            value = result.get(key)
            if isinstance(value, str):
                return value

    return str(result)


_BUILD_BANNER_LETTERS = {
    "B": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "],
    "U": ["██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "L": ["██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"],
    "D": ["██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "],
}
_BUILD_BANNER_COLORS = {
    "B": "bold red",
    "U": "bold blue",
    "I": "bold yellow",
    "L": "bold green",
    "D": "bold red",
}


def _render_build_banner() -> Text:
    """Render a multi-color 'BUILD' ASCII banner."""
    letters = "BUILD"
    rows = len(_BUILD_BANNER_LETTERS["B"])
    banner = Text()
    for row in range(rows):
        for ch in letters:
            banner.append(_BUILD_BANNER_LETTERS[ch][row], style=_BUILD_BANNER_COLORS[ch])
            banner.append("  ")
        if row < rows - 1:
            banner.append("\n")
    return banner


def _render_header(skill_names: list[str] | None = None) -> None:
    banner = _render_build_banner()
    title = Text("DEM333 // Build Agent Console", style="bold white on blue")
    subtitle = Text("Open-source frameworks x Microsoft Foundry", style="bold cyan")
    body = Text.assemble(
        ("Enter prompt", "bold white"),
        ("  |  ", "dim"),
        ("help", "bold yellow"),
        (" for commands", "dim"),
        ("  |  ", "dim"),
        ("clear", "bold yellow"),
        (" to reset", "dim"),
        ("  |  ", "dim"),
        ("exit", "bold yellow"),
        (" to quit", "dim"),
    )

    panel_content = Text.assemble(banner, "\n\n", title, "\n", subtitle)
    if skill_names:
        skills_line = Text.assemble(
            ("Skills: ", "dim"),
            *[
                part
                for i, name in enumerate(skill_names)
                for part in ((", ", "dim"),) * (1 if i > 0 else 0) + ((name, "bold magenta"),)
            ],
        )
        panel_content = Text.assemble(panel_content, "\n\n", skills_line)
    panel_content = Text.assemble(panel_content, "\n\n", body)

    console.print(Panel.fit(panel_content, border_style="bright_blue"))


def _render_help() -> None:
    console.print(
        Panel.fit(
            "\n".join(
                [
                    "help      Show command reference",
                    "clear     Clear screen and reset history",
                    "exit      End session",
                ]
            ),
            title="[bold yellow]Commands[/bold yellow]",
            border_style="yellow",
        )
    )


def _render_user_message(message: str) -> None:
    console.print(
        Panel(
            message,
            title="[bold white]You[/bold white]",
            border_style="green",
            expand=False,
        )
    )


def _render_assistant_message(message: str) -> None:
    console.print(
        Panel(
            Markdown(message),
            title="[bold cyan]DEM333 Agent[/bold cyan]",
            border_style="cyan",
            expand=True,
        )
    )


async def main(agent_builder: Callable[[], Awaitable[CompiledStateGraph]]) -> None:
    console.clear()
    
    agent = await agent_builder()

    # Diagnostic: discover which skills the agent loaded (same loader as SkillsMiddleware).
    skill_names, errors = await inspect_loaded_skills(agent)

    for err in errors:
        console.print(f"[bold red]Skill load error:[/bold red] {err}")

    await _run_chat_loop(agent, skill_names)


def _extract_skill_name(path: str) -> str:
    """Derive a human-readable skill name from a skill file path like /skills/inbox_triage/SKILL.md."""
    parts = [p for p in path.replace("\\", "/").split("/") if p and p.lower() != "skills"]
    # Drop the filename (e.g. SKILL.md) if there are multiple parts
    if len(parts) > 1:
        parts = parts[:-1]
    return parts[0].replace("_", " ").replace("-", " ").title() if parts else path


async def _invoke_with_skill_notifications(agent, agent_input: Any, agent_config: Any) -> Any:
    """Invoke the agent using v3 streaming, showing live activity nested under a spinner."""
    announced_skills: set[str] = set()
    last_message = None
    current_skill: str | None = None
    tool_calls: list[tuple[str, str]] = []

    spinner = Spinner("dots", text=Text("Agent thinking...", style="bold cyan"))

    def _format_tool_args(tool_input: Any) -> str:
        """Render tool arguments as a compact, single-line preview."""
        if not tool_input:
            return ""

        def _fmt_value(v: Any) -> str:
            if isinstance(v, str):
                s = v.replace("\n", " ").strip()
                if len(s) > 60:
                    s = s[:57] + "..."
                return repr(s)
            if isinstance(v, (int, float, bool)) or v is None:
                return repr(v)
            if isinstance(v, (list, tuple)):
                return f"[{len(v)} items]"
            if isinstance(v, dict):
                return f"{{{len(v)} keys}}"
            return type(v).__name__

        if isinstance(tool_input, dict):
            parts = [f"{k}={_fmt_value(v)}" for k, v in tool_input.items()]
            rendered = ", ".join(parts)
        else:
            rendered = _fmt_value(tool_input)

        if len(rendered) > 100:
            rendered = rendered[:97] + "..."
        return rendered

    def render() -> Group:
        """Render the spinner plus the current activity tree."""
        lines: list[Any] = [spinner]
        if current_skill:
            lines.append(Text.assemble(
                ("   ├─ ", "dim"),
                ("skill: ", "dim"),
                (current_skill, "bold magenta"),
            ))
        for i, (name, args) in enumerate(tool_calls):
            is_last = i == len(tool_calls) - 1
            connector = "   └─ " if is_last else "   ├─ "
            segments: list[Any] = [
                (connector, "dim"),
                ("tool:  ", "dim"),
                (name, "bold yellow"),
            ]
            if args:
                segments.extend([
                    ("(", "bright_black"),
                    (args, "bright_black"),
                    (")", "bright_black"),
                ])
            lines.append(Text.assemble(*segments))
        return Group(*lines)

    stream = await agent.astream_events(agent_input, config=agent_config, version="v3")

    with Live(render(), console=console, refresh_per_second=12, transient=True) as live:
        async for call in stream.tool_calls:
            tool_name = call.tool_name or "unknown"
            tool_input = call.input or {}

            # Extract any path-like arg the agent passed (skills are read via `read_file`).
            path = ""
            if isinstance(tool_input, dict):
                path = str(
                    tool_input.get("file_path", "")
                    or tool_input.get("path", "")
                    or ""
                )
            elif isinstance(tool_input, str):
                path = tool_input

            # Skill selection (progressive-disclosure step) — persistent announcement.
            if "/skills/" in path and path.endswith("SKILL.md") and path not in announced_skills:
                announced_skills.add(path)
                skill_label = _extract_skill_name(path)
                current_skill = skill_label
                # Persistent banner above the live display.
                live.console.print(Text.assemble(
                    (" ★ SKILL SELECTED ", "bold white on magenta"),
                    "  ",
                    (skill_label, "bold magenta"),
                ))
                live.update(render())
                continue

            # Append the tool to the running list so repeated calls remain visible.
            tool_calls.append((tool_name, _format_tool_args(tool_input)))
            live.update(render())

        async for message in stream.messages:
            last_message = message

    # Try to get the final output from stream.
    result = None
    try:
        result = await stream.output()
    except Exception as e:
        console.log(f"[dim]Stream output access failed ({type(e).__name__}: {e})[/dim]")

    # If no result from stream, construct from captured message.
    if result is None and last_message is not None:
        result = {"messages": [last_message]}

    # Last resort: fall back to plain invoke.
    if result is None:
        result = await agent.ainvoke(agent_input, config=agent_config)

    return result


async def _run_chat_loop(agent, skill_names: list[str] | None = None) -> None:
    _render_header(skill_names)

    thread_id = _new_thread_id()
    turn = 1

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]").strip()
            # Erase the echoed prompt line so only the rendered bubble is shown.
            console.file.write("\x1b[1A\x1b[2K\r")
            console.file.flush()
        except EOFError:
            console.print("\n[bold]Session closed.[/bold]")
            break
        except KeyboardInterrupt:
            console.print("\n[bold]Interrupted. Exiting.[/bold]")
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            console.print("\n[bold]Goodbye.[/bold]")
            break

        if user_input.lower() in HELP_COMMANDS:
            _render_help()
            continue

        if user_input.lower() in RESET_COMMANDS:
            thread_id = _new_thread_id()
            turn = 1
            console.clear()
            _render_header(skill_names)
            console.print("[dim]Conversation context reset.[/dim]")
            continue

        _render_user_message(user_input)

        try:
            agent_input: Any = {"messages": [HumanMessage(content=user_input)]}
            agent_config: Any = {"configurable": {"thread_id": thread_id}}
            result = await _invoke_with_skill_notifications(agent, agent_input, agent_config)
            assistant_text = _extract_text(result)
            console.print(Rule(style="bright_black"))
            _render_assistant_message(assistant_text)
            console.print(f"[dim]Turn {turn} complete[/dim]")
            turn += 1
        except KeyboardInterrupt:
            console.print("\n[bold]Interrupted. Exiting.[/bold]")
            break
        except Exception as exc:  # pragma: no cover - runtime/infra dependent
            console.print(f"[bold red]Agent call failed:[/bold red] {exc}")


def _resolve_agent_builder(agent_name: str) -> Callable[[], Awaitable[CompiledStateGraph]]:
    """Import only the selected teaching step so earlier steps stay dependency-light."""
    if agent_name == "base":
        from dem333.agent_base import build_agent
    elif agent_name == "mcp":
        from dem333.agent_mcp import build_agent
    elif agent_name == "skills":
        from dem333.agent_skills import build_agent
    else:
        from dem333.agent import build_agent

    return build_agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEM333 Build Agent Console")
    parser.add_argument(
        "--agent",
        choices=["demo", "mcp", "base", "skills"],
        default="demo",
        help="Agent type to load (default: demo)",
    )
    args = parser.parse_args()

    asyncio.run(main(agent_builder=_resolve_agent_builder(args.agent)))
