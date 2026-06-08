# a2a-directory

`a2a-directory` is a small A2A agent directory service used by the DEM333 demos.

## What is here

- `__main__.py`: Main CLI and MCP server entrypoint.
- `registry.py`: Agent registry loading and lookup.
- `client.py`: A2A invocation and tracing helpers.
- `server.py`: The MCP server.

## Quick start

From the repo root:

```bash
cd src/a2a-directory
uv sync
```

Run as an MCP server:

```bash
uv run python -m a2a-directory
```

Search agents from the command line:

```bash
uv run python -m a2a-directory --search "email triage"
```

Invoke a configured agent directly:

```bash
uv run python -m a2a-directory --agent-id my-agent --message "Summarize this inbox"
```

## Use from GitHub Copilot CLI

You can register this directory as an MCP server in [GitHub Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli) so Copilot can discover and call other A2A agents on your behalf. The server exposes two tools:

- `search_agent` — search the configured directory and return allowlisted agent IDs.
- `call_agent_a2a` — invoke one agent by ID with a message.

### Configure the server

Add an entry to your Copilot CLI MCP configuration (`~/.copilot/mcp-config.json`). Point `cwd` at this folder so `uv` resolves the project environment:

```json
{
  "mcpServers": {
    "a2a-directory": {
      "type": "local",
      "command": "uv",
      "args": ["run", "python", "-m", "a2a-directory"],
      "cwd": "/absolute/path/to/src/a2a-directory",
      "env": {
        "A2A_AGENTS_FILE": "/absolute/path/to/src/a2a-directory/directory.json"
      }
    }
  }
}
```

Alternatively, register it interactively from inside the CLI:

```bash
copilot
/mcp add
```

Then provide the same `command`, `args`, `cwd`, and environment values when prompted.

### Use it

Start Copilot CLI from this folder (or anywhere, since `cwd` is set above) and ask it to work with your agents. Run `/mcp` to confirm the `a2a-directory` server and its tools are loaded, then prompt naturally, for example:

```text
Search the agent directory for an email triage agent and ask it to summarize my inbox.
```

Copilot will call `search_agent` to find a matching agent ID and then `call_agent_a2a` to invoke it.

## Notes

- Python `>=3.14` is required (see `pyproject.toml`).
- `directory.json` should contain a JSON array of objects with at least `id` and `base_url`.
- Make sure you are logged in to Azure using `az login`.
- Keep credentials in environment variables or local `.env` files only.
