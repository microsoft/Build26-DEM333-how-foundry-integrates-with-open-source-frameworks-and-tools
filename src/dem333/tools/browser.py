"""LangChain tool that shells out to Microsoft's `@playwright/cli`.

The agent learns the command vocabulary from the `web-browsing` SKILL and
invokes this single tool with a free-form `args` string. Keeping the tool
schema minimal is intentional: it follows the upstream guidance that CLI +
SKILLS is more token-efficient than MCP because page snapshots and command
help never enter the model context unless the agent asks for them.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import shutil
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


DEFAULT_SESSION = "dem333"
MAX_OUTPUT_CHARS = 16_000
BLOCKED_SUBCOMMANDS = {"run-code", "eval"}
SHELL_METACHARS = (";", "|", "&", "&&", "||", "`", "$(", ">", "<")


class PlaywrightCliInput(BaseModel):
    """Input schema for the `playwright_cli` tool.

    An explicit Pydantic schema avoids LangChain's `v__args` positional-input
    fallback when the model emits a single-string argument.
    """

    args: str = Field(
        ...,
        description=(
            "Playwright CLI command (without the leading `playwright-cli`). "
            'Examples: "open https://example.com", "snapshot", "click e15", '
            '"fill e3 \\"hello\\"".'
        ),
    )
    session: Optional[str] = Field(
        default=None,
        description="Optional named browser session. Defaults to 'dem333'.",
    )
    timeout_seconds: int = Field(
        default=60,
        description="Maximum time to wait for the command to complete.",
    )


def _resolve_binary() -> list[str]:
    """Return argv prefix for invoking playwright-cli.

    Prefer a globally installed `playwright-cli`; fall back to
    `npx --no-install playwright-cli` as documented upstream.
    """
    if shutil.which("playwright-cli"):
        return ["playwright-cli"]
    if shutil.which("npx"):
        return ["npx", "--no-install", "playwright-cli"]
    raise RuntimeError(
        "playwright-cli not found. Install with `npm install -g @playwright/cli@latest` "
        "or ensure `npx` is on PATH."
    )


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    head = text[: MAX_OUTPUT_CHARS - 200]
    return f"{head}\n\n[...output truncated to {MAX_OUTPUT_CHARS} chars; use `snapshot --depth=N` or `--raw` to narrow output...]"


@tool(args_schema=PlaywrightCliInput)
async def playwright_cli(
    args: str,
    session: Optional[str] = None,
    timeout_seconds: int = 60,
) -> str:
    """Execute a Playwright CLI command and return its combined stdout/stderr.

    Pass the command portion only (no leading `playwright-cli`). For example:
    `open https://example.com`, `snapshot`, `click e15`, `fill e3 "hello"`.

    A persistent browser session is shared across calls via `-s=<session>`
    (default: `dem333`). Pass `session=` to address a different browser.

    The full command vocabulary is documented in the `web-browsing` skill.
    """
    if not args or not args.strip():
        return "Error: `args` is empty. Provide a playwright-cli command, e.g. `snapshot`."

    for bad in SHELL_METACHARS:
        if bad in args:
            return f"Error: shell metacharacter {bad!r} is not allowed in args."

    try:
        argv_tail = shlex.split(args)
    except ValueError as exc:
        return f"Error: could not parse args ({exc})."

    if argv_tail and argv_tail[0] in BLOCKED_SUBCOMMANDS:
        return (
            f"Error: subcommand `{argv_tail[0]}` is disabled in this agent for safety. "
            "Use `snapshot`, `click`, `fill`, `type`, etc., instead."
        )

    # Auto-inject --headed on `open` when env requests it (live demos).
    if (
        argv_tail
        and argv_tail[0] == "open"
        and os.getenv("PLAYWRIGHT_CLI_HEADED", "").lower() in {"1", "true", "yes"}
        and "--headed" not in argv_tail
    ):
        argv_tail.append("--headed")

    session_name = session or os.getenv("PLAYWRIGHT_CLI_SESSION") or DEFAULT_SESSION

    try:
        binary = _resolve_binary()
    except RuntimeError as exc:
        return f"Error: {exc}"

    argv = [*binary, f"-s={session_name}", *argv_tail]

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        return f"Error: failed to launch playwright-cli ({exc})."

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"Error: playwright-cli timed out after {timeout_seconds}s. Args: {args}"

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")

    parts: list[str] = []
    if stdout.strip():
        parts.append(stdout.rstrip())
    if stderr.strip():
        parts.append(f"[stderr]\n{stderr.rstrip()}")
    if proc.returncode != 0:
        parts.append(f"[exit code {proc.returncode}]")

    return _truncate("\n\n".join(parts) or "[no output]")
