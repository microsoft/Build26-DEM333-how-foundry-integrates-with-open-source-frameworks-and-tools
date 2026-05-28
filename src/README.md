# DEM333 source code

The session demo source is in [`dem333/`](dem333/).

## What is included

- Three Responses-protocol hosted agents: coordinator, itinerary, and policy
- Microsoft Agent Framework coordinator workflow
- LangGraph itinerary specialist
- A2A and Responses clients
- MCP stdio action server/client
- Agent Framework skills
- AG-UI HTTP/SSE gateway
- OpenTelemetry tracing helpers
- Interactive talk plan for Outlook MCP and Copilot CLI external-agent observability
- Dockerfiles, Foundry agent metadata, and Azure infrastructure scaffold

## Quick start

```bash
cd src/dem333
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 scripts/run_demo.py
```

See [`dem333/README.md`](dem333/README.md) for full setup, AG-UI, hosted-agent, tracing instructions, and the interactive talk plan.
