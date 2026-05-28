# DEM333 multi-agent demo

DEM333 is a Foundry-ready multi-agent demo that shows how a coordinator can bring specialist agents together through open agent surfaces, then use Foundry/App Insights observability to inspect the whole run. The updated live plan makes the session interactive: Fauncdo asks for new capabilities, Nagkumar adds them in small steps, and the audience watches the hosted response and trace evolve. The scenario is an executive customer-visit planner that can start from Outlook email context, delegate to itinerary and policy specialists, perform safe prep actions, and return a final briefing plan with action receipts.

## What is in this folder

| Area | Path | What it contains |
| --- | --- | --- |
| Coordinator agent | `agents/coordinator_agent/` | Responses-protocol hosted agent. Uses Microsoft Agent Framework `WorkflowBuilder` to plan delegation, call specialists, perform actions, and synthesize the answer. |
| Itinerary specialist | `agents/itinerary_agent/` | Responses-protocol hosted agent. Uses LangGraph nodes for request parsing, schedule drafting, critique, MCP-backed actions, and final formatting. |
| Policy specialist | `agents/policy_agent/` | Responses-protocol hosted agent. Uses LLM calls plus Agent Framework skills to produce compliance/readiness guidance and action receipts. |
| Shared runtime helpers | `src/dem333_common/` | A2A client, Responses client, OTel setup, LangChain model factory, MCP stdio server/client, skills, action receipts, and text helpers. |
| Local demo runner | `scripts/run_demo.py` | Starts all three agents locally, sends one coordinator request, prints the response, then dumps console OTel spans. |
| Foundry deployment assets | `agents/*/Dockerfile`, `agents/*/agent.yaml` | Container and hosted-agent metadata for each agent. |
| Azure infra | `infra/` | Azure Developer CLI/Bicep scaffolding for Foundry/App Insights infrastructure. |
| Talk material | `docs/interactive-demo-plan.md`, `docs/talk-script.md` | Interactive demo plan, back-and-forth speaker script, trace callouts, and fallback narration. |

## Demo surfaces

| Surface | Where to point during the demo |
| --- | --- |
| Responses API/protocol | All three agents expose `/responses`; local coordinator invokes specialists through Responses requests. |
| A2A | Hosted coordinator can invoke the two specialist agents through A2A `message/send` JSON-RPC endpoints. |
| LangGraph | `itinerary_agent` graph nodes: `parse_request`, `draft_schedule`, `critique_schedule`, `perform_actions`, `format_answer`. |
| Microsoft Agent Framework | `coordinator_agent` uses MAF workflow executors for delegation, specialist calls, actions, and synthesis. |
| Skills | `policy_agent` and `coordinator_agent` create action receipts through Agent Framework `InlineSkill` definitions. |
| MCP | `itinerary_agent` and `coordinator_agent` call the official Python MCP SDK over stdio to `dem333-action-mcp` tools. |
| Outlook MCP live beat | The talk plan layers an Outlook/Microsoft Graph MCP server onto the hosted coordinator so a demo mailbox can feed the visit plan. |
| AG-UI | `dem333_common.agui_gateway` exposes an AG-UI HTTP/SSE endpoint that streams coordinator runs to user-facing apps. |
| OpenTelemetry | Every surface stamps spans with `dem333.surface` plus GenAI semantic attributes for Foundry/App Insights inspection. |
| External agent observability | The final talk beat uses Copilot CLI as an external agent, follows the [Foundry external agents observability sample](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/external-agents/observability), exports SDK traces to the same App Insights resource, and makes an A2A call into the hosted coordinator. |

The checked-in local demo remains deterministic and safe to run without Outlook or Copilot CLI. The live talk plan layers Outlook MCP and Copilot CLI external-agent tracing on top of the same hosted-agent architecture.

## Interactive live plan

The revised talk uses a back-and-forth format:

1. Fauncdo asks whether the agent can read email.
1. Nagkumar connects Outlook through MCP and shows a hosted response.
1. Fauncdo asks for better planning, policy checks, a user-facing stream, and another agent calling this one.
1. Nagkumar adds MAF/LangGraph orchestration, hosted A2A specialists, AG-UI, and finally Copilot CLI as an external agent that calls the coordinator over A2A.
1. Each step ends in Foundry/App Insights so the audience can see the trace, not just the answer.

See [`docs/interactive-demo-plan.md`](docs/interactive-demo-plan.md) and [`docs/talk-script.md`](docs/talk-script.md).

## Agent roles and actions

| Agent | Role | Actions performed |
| --- | --- | --- |
| `dem333-coordinator-agent` | Orchestrates the overall request and delegates to specialists. | Creates an executive summary receipt through a skill and opens a follow-up task through MCP. |
| `dem333-itinerary-agent` | Builds the customer-visit plan with LangGraph. | Reserves a synthetic briefing room and creates an executive brief through MCP. |
| `dem333-policy-agent` | Reviews compliance, privacy, accessibility, procurement, and commitment risks. | Creates human policy-review and readiness-checklist receipts through skills. |

The checked-in actions are intentionally synthetic and demo-safe: they return receipts and trace attributes, but do not book real rooms, send emails, create tickets, or touch customer systems. For the live Outlook beat, use a dedicated demo mailbox, read-only permissions, and sanitized trace content.

## Local run

```bash
cd src/dem333
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 scripts/run_demo.py
```

Required environment values for real LLM calls:

```bash
AZURE_OPENAI_ENDPOINT=https://<account>.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4-1-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_MODEL_NAME=gpt-4.1-mini
```

`scripts/run_demo.py` starts each agent on a local port, sends one coordinator request, prints the response, and shuts everything down. It enables console OpenTelemetry spans and content recording so you can show model inputs, outputs, MAF workflow steps, LangGraph nodes, skills, MCP tool calls, and action receipts before deploying to Azure resources.

## AG-UI gateway

AG-UI is the user-facing application protocol layer for the demo. It complements the other protocols:

- **AG-UI** connects the DEM333 agent system to a frontend or CopilotKit-style app.
- **A2A** connects the coordinator to hosted specialist agents.
- **MCP** connects agents to tools/actions.
- **OTel** makes every event, handoff, and action observable.

Run the gateway after the local coordinator is running:

```bash
. .venv/bin/activate
PYTHONPATH=src DEM333_COORDINATOR_RESPONSES_URL=http://127.0.0.1:8010/responses \
  python3 scripts/run_agui_gateway.py
```

The gateway listens on `DEM333_AGUI_PORT` or `8020` by default and accepts AG-UI `RunAgentInput` at `/` or `/agui`:

```bash
curl -N -X POST http://127.0.0.1:8020/agui \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "threadId": "dem333-thread",
    "runId": "dem333-run",
    "state": {},
    "messages": [
      {
        "id": "msg-1",
        "role": "user",
        "content": "Plan a 2-day customer visit to Seattle for a healthcare customer."
      }
    ],
    "tools": [],
    "context": [],
    "forwardedProps": {}
  }'
```

Expected stream highlights:

- `RUN_STARTED`
- `STATE_SNAPSHOT` with the DEM333 surfaces
- `STEP_STARTED` / `STEP_FINISHED` for invoking the coordinator
- `TOOL_CALL_*` / `TOOL_CALL_RESULT` showing the coordinator Responses call
- `TEXT_MESSAGE_*` streaming the final coordinator answer
- `RUN_FINISHED` or `RUN_ERROR`

### Deploy the AG-UI gateway

The AG-UI gateway is not a Foundry hosted agent. Deploy it as a small web runtime in front of the Foundry coordinator, for example with Azure Container Apps:

```bash
az acr build \
  --registry <acr-name> \
  --image dem333-agui-gateway:<tag> \
  --platform linux/amd64 \
  --source-acr-auth-id "[caller]" \
  --file Dockerfile.agui .
```

Set these runtime environment variables:

```bash
DEM333_COORDINATOR_RESPONSES_URL=<deployed coordinator Responses endpoint>
APPLICATION_INSIGHTS_CONNECTION_STRING=<same App Insights connection string as the agents>
PORT=8080
```

Assign the gateway's managed identity `Azure AI User` on the Foundry account so it can call the coordinator Responses endpoint with `DefaultAzureCredential`.

## Hosted-agent handoff

Each agent folder includes an `agent.yaml` and `Dockerfile`. Build each image from the `dem333` root so the Dockerfile can copy the shared `src/` package:

```bash
docker build --platform linux/amd64 -f agents/policy_agent/Dockerfile -t dem333-policy-agent .
docker build --platform linux/amd64 -f agents/itinerary_agent/Dockerfile -t dem333-itinerary-agent .
docker build --platform linux/amd64 -f agents/coordinator_agent/Dockerfile -t dem333-coordinator-agent .
```

In the hosted demo, deploy the policy and itinerary specialists as Responses-protocol hosted agents, enable incoming A2A on those specialists, then configure the coordinator with:

```bash
DEM333_COORDINATOR_TRANSPORT=a2a
POLICY_AGENT_A2A_URL=<policy A2A endpoint>
ITINERARY_AGENT_A2A_URL=<itinerary A2A endpoint>
APPLICATION_INSIGHTS_CONNECTION_STRING=<App Insights linked to the Foundry project>
DEM333_LANGCHAIN_TRACING=true
DEM333_TRACE_CONTENT=true
```

Invoke the coordinator through the Foundry/Responses endpoint. The hosted trace should include:

- top-level Foundry hosted-agent invocation
- MAF coordinator spans with `dem333.surface=maf`
- A2A `message/send` spans with `dem333.surface=a2a`
- AG-UI gateway spans with `dem333.surface=ag-ui`
- specialist Responses spans with `dem333.surface=responses-protocol`
- LangGraph node/model spans from `langchain-azure-ai`
- MCP tool spans with `dem333.surface=mcp`
- skill spans with `dem333.surface=skill`
- model input/output attributes when content tracing is enabled

## Talk narrative

The short version: "We start with a hosted coordinator behind Responses. Fauncdo asks whether it can get email, so we connect Outlook through MCP. As the asks get richer, we add MAF orchestration, LangGraph and policy specialists over A2A, skills, AG-UI streaming, and finally Copilot CLI as an external agent making its own A2A call. Every handoff, tool call, and model call is visible with OpenTelemetry in Foundry."

Use `docs/interactive-demo-plan.md` for the live arc and `docs/talk-script.md` for the back-and-forth speaker script and stage directions.
