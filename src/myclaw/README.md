# myclaw

`myclaw` is the DEM333 agent app used in this repository.

## What is here

- `main.py`: Interactive CLI chat experience for the agent.
- `server.py`: Hosted server entrypoint using `ResponsesHostServer`.
- `myclaw/`: Agent implementation, prompts, skills, and tools.
- `Dockerfile`: Container build for hosted scenarios.

## Quick start

From the repo root:

```bash
cd src/myclaw
uv sync
uv run main.py
```

To run the hosted server locally:

```bash
cd src/myclaw
uv run server.py
```

Default server port is `8088`. You can change it with:

```bash
PORT=8090 uv run server.py
```

## Notes

- Python `>=3.14` is required (see `pyproject.toml`).
- Keep secrets in environment variables or local `.env` files only.
