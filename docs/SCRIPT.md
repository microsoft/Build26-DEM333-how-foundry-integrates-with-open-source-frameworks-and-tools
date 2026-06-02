# DEM333 - Demo Script

**Session:** How Foundry Integrates With Open Source Frameworks and Tools
**Speakers:** **Facundo** (narrator / asks the questions) and **Nagkumar** (drives VS Code, terminal, and Foundry)
**Duration target:** 30 minutes
**Demo project:** `src/` - a homegrown "OpenClaw-style" agent built with LangGraph, MCP, Skills, Playwright, and Microsoft Foundry.

## Story in one sentence

We start with ordinary open-source agent code, progressively add real tools and skills, then move the same LangGraph agent into Foundry so it can be invoked through the Responses API, observed with OpenTelemetry, and called by another agent through A2A.

## What must land

1. The agent starts as simple LangGraph/deepagents code using `init_chat_model("openai:gpt-5.2")`.
2. MCP gives the agent real Microsoft 365 tools through Work IQ Mail.
3. Skills teach the agent how to use tools safely and repeatably.
4. Playwright CLI shows the "sophisticated tool" pattern without bloating the model context.
5. Foundry hosts the same agent behind the OpenAI-compatible Responses API.
6. App Insights / OpenTelemetry shows the graph, model, tool calls, latency, and captured input/output.
7. A2A lets Copilot CLI discover and call the hosted agent through a small local A2A directory exposed as MCP.

> **Conventions**
>
> - **F:** Facundo speaking.
> - **N:** Nagkumar speaking.
> - *(stage)* Action on screen or hand-off cue.
> - **Prompt card:** Exact prompt to type during rehearsal.
> - **Fallback:** What to say or do if a live service is slow.
>
> **Live-action cadence for Nagkumar:** before every action that can take time, say what you are about to do, do it on screen, then explain what the audience should watch for while it runs. Do not leave silent terminal or portal time.

---

## Current demo state to reflect during rehearsal

- The main final agent is `src/dem333/agent.py`.
- The hosted agent name is `dem333-openclaw-agent-stitched`.
- The hosted endpoint is enabled for both `responses` and `a2a`.
- The currently rehearsed hosted deployment routes to the latest validated version; verify before going on stage because this can change after redeploys.
- Work IQ uses `DEM333_WORK_IQ_CLIENT_ID` / `WORK_IQ_CLIENT_ID`; do **not** put the Work IQ public-client app ID in `AZURE_CLIENT_ID` for hosted deployments.
- The Copilot CLI integration is the generic A2A directory server in `dem333.a2a`.
- A2A is not a wrapper around MCP. A2A is how another agent discovers and calls our hosted agent. The local MCP bridge exists only because Copilot CLI can consume MCP tools today.

---

## 1. Hook - why this matters - 3 min

*(stage) Title slide is up. Camera on both speakers.*

**F:** Hi everyone! Welcome to **How Foundry Integrates With Open Source Frameworks and Tools**. My name is Facundo and today... I'm joined by Nagkumar who is going to drive the demo.

**F:** Today's question is simple: if your agent already exists in LangGraph, MCP, or plain Python, how do you move it to production without rewriting it?

*(stage) Switch to a single slide: "Goal: build our own OpenClaw using only open-source pieces, then graduate it to Foundry."*

**F:** And for that, we brought an interesting setup. You've seen agents like *OpenClaw*: they can browse the web, read email, and take action across tools. Today, we are going to **build our own OpenClaw-style agent, live**, using open-source frameworks and tools.

*(stage) Slide: "Open-source agent code -> real tools -> hosted in Foundry -> observable -> callable by other agents.")*

**F:** We are going to show how **Microsoft Foundry takes that exact same code and supercharges it**. Sounds fun? Let's get started.

---

## 2. Minimal agent loop in LangGraph - 3 min

**F:** So, let's start at the bottom. If I want to build an agent today - no hosting, no platform magic - what's the smallest amount of code I need?

*(stage) Open `src/dem333/agent_base.py`.)*

**N:** At the core, we need a model and an agent loop. The agent loop is what keeps the agent moving: it asks the model for the next step, runs tools when needed, and uses each result to decide what happens next. This file is intentionally small. The model comes from LangChain's `init_chat_model`, and the loop is built with `create_deep_agent`.

*(stage) Highlight the core lines.)*

```python
model = init_chat_model("openai:gpt-5.2")

return create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)
```

**N:** The important point is that this is ordinary LangChain/LangGraph-style code. Most Foundry models expose OpenAI-compatible APIs, so LangChain can talk to a Foundry model deployment using the protocol it already understands. The model target is configuration, not a rewrite.

**F:** So in this case, LangChain owns the agent loop, and Foundry provides the model via the OpenAI-compatible protocol.

**N:** Right. I'll run the smallest local agent first. It takes a few seconds to boot, so while it starts, watch for the DEM333 banner and notice that this is still just local Python - no hosted endpoint yet.

---

## 3. First interaction in the console - 1.5 min

*(stage) Open integrated terminal. Venv already active. From repo root, remember the Python project is under `src/`.)*

```bash
cd src
uv run --env-file .env python main.py --agent base
```

**N:** While it starts, notice that the framework loop is doing the work. We are not calling the hosted agent yet; the only production-facing dependency is the model behind `init_chat_model`.

**Prompt card**

```text
Hello! In one sentence, tell me what you can help with.
```

*(stage) Type the prompt. The DEM333 banner appears, the agent replies with a generic assistant response.)*

**N:** This is useful, but it's still only a brain. If I ask it to read my email, it doesn't have any hands.

**F:** Right. One reason agents like OpenClaw are useful is that they can do things. What is the usual pattern for giving an agent tools?

---

## 4. Tools via MCP - connecting Work IQ Mail - 4.5 min

**N:** The open-source pattern is MCP - Model Context Protocol. MCP is an open protocol that lets an agent discover tools and call them. For this demo, the MCP server is **Work IQ Mail**, which gives the agent access to Microsoft 365 mail capabilities through a tool interface.

*(stage) Open `src/dem333/tools/work_iq.py`.)*

**N:** The agent does not need to know every HTTP endpoint in Microsoft 365. It connects to the Work IQ MCP server, asks for tools, and receives tool schemas like search messages, get message details, draft replies, and so on.

*(stage) Open `src/dem333/agent_mcp.py` and highlight the MCP client wiring.)*

```python
connections: dict[str, Any] = {"mail": build_work_iq_mail_connection()}
return MultiServerMCPClient(connections)
```

**N:** Then we pass the discovered MCP tools into the same agent loop:

```python
mcp_tools = await mcp_client.get_tools()
return configure_work_iq(mcp_tools)
```

**F:** So you're saying I can take *any* LangGraph agent I already have, and just plug this server over the open protocol to give it access to Work IQ?

**N:** Exactly. I'll restart with the MCP-enabled agent now. The next request may pause while the tool connection is established, so while it runs, watch for tool discovery and the Work IQ / Mail MCP call rather than just the final text.

*(stage) Restart with the MCP-enabled agent.)*

```bash
uv run --env-file .env python main.py --agent mcp
```

**Prompt card - privacy-safe for rehearsal**

```text
check my email
```

*(stage) The spinner shows Work IQ / Mail MCP tool calls. The final answer should be compact and privacy-safe.)*

**N:** While that spinner is moving, watch the tool boundary. The agent discovered the mail tools at runtime and chose the right one. We are also keeping the output privacy-safe.

**N:** Now the same local agent can call Microsoft 365 through MCP. The tool boundary is open and inspectable, and the agent still remains normal Python code.

**Fallback:** If auth expires or mail is slow, say: "This is why we preflight Work IQ before going on stage. The important artifact is that the agent discovered and attempted the MCP mail tool; the hosted version is already validated, so we'll continue with the prepared flow."

---

## 5. Skills - teaching the agent how to use tools - 4 min

**F:** Great. The agent now has hands, but we want more than that. "Check my email" is useful, but "triage my inbox" saves time. Do I need to tell it every step?

**N:** That's where Skills come in. A tool is a verb: "search messages." A Skill is a playbook: "when triaging inbox, pull minimal fields first, classify into categories, assign P0-P3 priority, avoid exposing private message content, and draft only when asked."

*(stage) Open `src/dem333/skills/inbox-triage/SKILL.md`.)*

**N:** A Skill is simple: it is a markdown playbook with a small frontmatter block. No special service. No proprietary schema. The agent reads it only when the prompt is relevant.

**N:** Now I'll restart with the Skills-enabled agent. This can take a moment because the agent has to decide whether the prompt is relevant to a Skill, read that Skill, then use the same Work IQ tools under that guidance.
*(stage) Restart with the skills-enabled agent.)*

```bash
uv run --env-file .env python main.py --agent skills
```

**Prompt card**

```text
triage my inbox
```

*(stage) Watch for the skill load notice and Work IQ tool calls.)*

**F:** While this runs, how is the agent finding these skills we wrote?

*(stage) Open `src/dem333/agent_skills.py` and highlight the virtual filesystem route.)*

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/skills/": FilesystemBackend(root_dir="dem333/skills", virtual_mode=True),
    },
)
```

**N:** We mount the local `dem333/skills` folder into a virtual `/skills/` path. The agent can list and read the markdown when it needs guidance.

**N:** Let's go back to the terminal. Watch for two things: first the Skill selection, then the Work IQ tool call. The point is simple: tools give capability, and Skills make the behavior repeatable.

**F:** That's bold. Same model, same tools — but totally different behavior because of the reusable skill.

**N:** That's the big point. Skills are a lightweight way to make agent behavior repeatable without turning every instruction into a massive system prompt.

---

## 6. Sophisticated tools - Playwright browser - 4 min

**F:** The other thing people expect from an OpenClaw-style agent is browser work. What is the open-source pattern there?

*(stage) Open `src/dem333/skills/web-browsing/SKILL.md`, then `src/dem333/tools/browser.py`.)*

**N:** For that, we can use Playwright, an open-source framework that allows developers (and agents) to control browsers using a single API. Here we use `@playwright/cli`: one command-line tool, plus a Skill that teaches the agent the command vocabulary.

*(stage) Open final agent `src/dem333/agent.py` and highlight that both Work IQ tools and `playwright_cli` are returned.)*

```python
return configure_work_iq(mcp_tools) + [playwright_cli]
```

**N:** I'll run the final local demo agent now and give it a browser task. Browser automation is intentionally slower than a chat-only response, so while it runs, I'll point out the skill/tool pattern instead of waiting silently.

*(stage) Run the final local demo agent.)*

```bash
uv run --env-file .env python main.py --agent demo
```

**Prompt card - primary**

```text
Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find. Do not sign in, add anything to cart, or check out. If the site blocks browsing, say it was blocked.
```

**F:** While this runs, I'm wondering - why did we use a different approach here compared to the MCP server from Work IQ?

**N:** We could use an MCP server, but browser work can create a large tool surface. Here the command line is simpler. The Python tool has one `args` string and an optional browser session. Snapshots and command details only enter the context when the agent asks for them.

**F:** Got it. So it is easier for the model, and it is more token efficient. The result is back now, and the browser flow is the proof.

**Prompt card - safer fallback**

```text
Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.
```

*(stage) Spinner should show `skill: Web Browsing`, then `playwright_cli` commands such as `open`, `snapshot`, `type`, `press`, and `click`.)*

**N:** While the browser steps run, notice that the model did not receive a giant browser API surface. It chose the Web Browsing Skill, then drove one Playwright CLI tool through a sequence of small commands and snapshots.

**F:** The important part is not Amazon. The important part is that the agent selected the browser skill, used a single powerful tool safely, and kept the browser state across steps.

**N:** Exactly. For live demos, public websites can block automation, so the fallback is the Build session page. The story still lands because the tool pattern is the same.

---

## 7. From console to cloud - Foundry Responses API - 3 min

**F:** Now, fair question from the audience: this is running in a terminal, but production users are not going to use your laptop. How do we take this to production?

*(stage) Open `src/server.py`.)*

**N:** This is where Foundry steps in. Foundry hosts the same LangGraph agent and exposes it through an OpenAI-compatible Responses API. This file is the adapter layer. Notice that we still call the same `build_agent()` from `dem333.agent`.

```python
app = ResponsesAgentServerHost(
    applicationinsights_connection_string=_app_insights_connection_string(),
)

agent = await build_agent()

host = ResponsesHostServer(
    graph=agent,
    app=app,
)
```

**N:** There are two details worth calling out:

1. `ResponsesHostServer` exposes the LangGraph agent as a Responses-compatible endpoint.
2. We initialize the Foundry server host before building the graph so OpenTelemetry/LangChain instrumentation can attach before the graph is constructed.

**F:** If I'm reading this correctly, you are wrapping the agent in the protocol. So the same code path can run locally in the console or remotely, right?

**N:** Correct. For the talk, the agent is already deployed as `dem333-openclaw-agent-stitched`.

**N:** I'll send one hosted smoke request next. Hosted calls can take a moment if the container is warming, so while it runs, I'll call out that this is the same `build_agent()` path now reached through the Responses API.

*(stage) Optional: show the shape of the smoke test, not the full JSON response.)*

```bash
export FOUNDRY_TOKEN=$(az account get-access-token \
  --resource https://ai.azure.com \
  --query accessToken -o tsv)

curl -sS -X POST \
  -H "Authorization: Bearer ${FOUNDRY_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Foundry-Features: HostedAgents=V1Preview" \
  "${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/openai/responses?api-version=2025-11-15-preview" \
  -d '{"input":"Reply with exactly: DEM333 hosted ready","stream":false}'
```

**Prompt card - hosted smoke**

```text
triage my inbox
```

*(stage) Send the hosted smoke prompt through the endpoint or Foundry playground.)*

**N:** While the request is in flight, the important adapter is `ResponsesHostServer`: OpenAI-compatible clients talk to the hosted endpoint, and our LangGraph agent still runs behind it.

**Fallback:** If the live API is slow, switch to the Foundry playground for the same agent and say: "The protocol is the same; the playground is just another client of the hosted agent."

---

## 8. Observability - OpenTelemetry and App Insights - 3 min

**F:** Okay. We got the agent to the cloud. The next production question is: can we see what it is doing?

**N:** Yes. Foundry integrates with Application Insights and OpenTelemetry. The demo uses the Microsoft OpenTelemetry distro and GenAI semantic conventions, so we can inspect the LangGraph span, model calls, tool calls, latency, and captured input/output.

*(stage) Open Foundry monitoring or App Insights traces for `dem333-openclaw-agent-stitched`.)*

**N:** In the trace, look for these beats:

1. `invoke_agent LangGraph` is the parent span for the agent run.
2. `model` / `chat gpt-5.2...` shows the model call.
3. `tools` and `execute_tool ...` show Work IQ or browser activity.
4. Dependency spans show external calls, for example Work IQ MCP and Azure OpenAI.
5. For the rehearsal deployment, `gen_ai.input.messages` and `gen_ai.output.messages` are captured so we can verify the request/response path.

**N:** The content capture is intentional for this demo and enabled by these environment variables. In a real production rollout, decide this based on your organization's privacy and retention policy.

```bash
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT="SPAN_AND_EVENT"
export OTEL_SEMCONV_STABILITY_OPT_IN="gen_ai_latest_experimental"
export AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING="true"
```

**F:** And OpenTelemetry with semantic conventions means the data uses an industry format. We can read it with different tools. No lock-in, just telemetry.

**N:** I'll generate one small request to create fresh telemetry. The trace view may lag by a few seconds, so while it runs, I'll explain the spans we expect to see.

**Prompt card - generate trace traffic**

```text
triage my inbox
```

*(stage) Send the prompt through the hosted endpoint or Foundry playground, then switch back to the trace view.)*

**N:** While it is running, watch for four spans or attributes: the LangGraph parent span, the model call, any tool calls, and captured input/output.

**Fallback:** If the portal view is slow, use a prepared App Insights query result that shows recent `invoke_agent LangGraph` rows with non-empty input and output capture counts.

---

## 9. A2A - calling the hosted agent from Copilot CLI - 2 min

**F:** Last question. Everyone is talking about agents working with other agents. Can another agent call this one?

**N:** Yes. Once the Foundry A2A endpoint is enabled, another A2A-compatible client can discover the agent card and send messages to the hosted agent.

**N:** For Copilot CLI specifically, the current integration point is MCP tools. So we expose a tiny local A2A directory as an MCP server. Copilot can search configured agents, choose one, and then call it over A2A. That does **not** mean A2A is MCP. It means MCP is the local adapter Copilot CLI can load today.

*(stage) Open `src/dem333/a2a/__main__.py` and highlight the tools.)*

```python
@mcp.tool()
async def search_agent(query: str = "") -> list[dict[str, Any]]:
    """Search the configured A2A agent directory."""

@mcp.tool()
async def call_agent_a2a(agent_id: str, message: str, ctx: Context) -> str:
    """Call one configured A2A agent by ID. Use search_agent first."""
```

**N:** Instead of doing a separate smoke test, I'll go straight to the real A2A call from Copilot CLI. Startup and tool registration can take a moment, so while it opens, watch for two tool names: `search_agent` and `call_agent_a2a`.

*(stage) Then start Copilot CLI with the bridge.)*

```bash
cd src
export FOUNDRY_A2A_URL="${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/a2a"
export FOUNDRY_A2A_AGENT_CARD_PATH="agentCard/v0.3"
export APPLICATIONINSIGHTS_CONNECTION_STRING="${APPLICATION_INSIGHTS_CONNECTION_STRING}"

cat > /tmp/copilot-a2a-bridge.json <<JSON
{
  "mcpServers": {
    "a2a-directory": {
      "command": "uv",
      "args": ["--directory", "$PWD", "run", "--env-file", ".env", "python", "-m", "dem333.a2a"],
      "env": {
        "FOUNDRY_A2A_URL": "$FOUNDRY_A2A_URL",
        "FOUNDRY_A2A_AGENT_CARD_PATH": "agentCard/v0.3",
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "$APPLICATION_INSIGHTS_CONNECTION_STRING"
      }
    }
  }
}
JSON

copilot --additional-mcp-config @/tmp/copilot-a2a-bridge.json --allow-all-tools --allow-all-urls
```

**Prompt card - inside Copilot CLI**

```text
triage my inbox
```

*(stage) Copilot CLI calls `search_agent`, selects the configured DEM333 agent, calls `call_agent_a2a`, the directory invokes the Foundry A2A endpoint, the hosted LangGraph agent uses Work IQ MCP and Skills, and the answer appears back in Copilot CLI.)*

**N:** While Copilot is waiting, trace the chain with me: Copilot CLI searches the local A2A directory, calls the selected agent through A2A, the hosted LangGraph agent runs, and that hosted agent can still use Work IQ MCP and Skills.

**F:** Pause on what just happened. Copilot CLI, a totally different agent runtime, searched an A2A directory exposed as MCP, selected a configured agent, and crossed into A2A. A2A reached our LangGraph agent hosted in Foundry, which then used Work IQ MCP server, applied a skill, and answered. **None of those pieces had to know about each other.** Impressive.

**N:** And here is the extra payoff. The trace follows that handoff. In App Insights, the local directory span `invoke_agent dem333-openclaw-agent-stitched` and the hosted `invoke_agent LangGraph` span share the same operation ID, so we can explain interop and observability on one screen.

**N:** That is the open-source integration story: framework, tools, skills, hosting, telemetry, and agent-to-agent interoperability.

---

## 10. Wrap-up - 1.5 min

*(stage) End slide with QR code / repo URL.)*

**F:** You are right to call that out because that's the power of the open-source integration story. And that's the story we want you to take from this session. I think it's a wrap, right?

**N:** The code is available in the repo, and the demo is structured so you can run the same steps locally or as a hosted Foundry agent.

**F:** Thanks everyone. We'll stick around for questions.

---

## Timing budget recap

| Section | Time | Cumulative |
|---|---:|---:|
| 1. Hook / why this matters | 3:00 | 3:00 |
| 2. LangGraph agent loop | 3:00 | 6:00 |
| 3. First console interaction | 1:30 | 7:30 |
| 4. MCP - Work IQ Mail | 4:30 | 12:00 |
| 5. Skills - inbox triage | 4:00 | 16:00 |
| 6. Playwright browser | 4:00 | 20:00 |
| 7. Responses API on Foundry | 3:00 | 23:00 |
| 8. OpenTelemetry | 3:00 | 26:00 |
| 9. A2A from Copilot CLI | 2:00 | 28:00 |
| 10. Wrap-up / Q&A buffer | 2:00 | 30:00 |

---

## Rehearsal prompt cards

Use these exact prompts when practicing so the telemetry and stage flow are predictable.

| Demo beat | Prompt |
|---|---|
| Base console | `Hello! In one sentence, tell me what you can help with.` |
| Work IQ MCP | `check my email` |
| Inbox skill | `triage my inbox` |
| Browser primary | `Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find. Do not sign in, add anything to cart, or attempt checkout. If the site blocks browsing, say it was blocked.` |
| Browser fallback | `Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.` |
| Hosted Responses | `triage my inbox` |
| Telemetry | `triage my inbox` |
| Copilot CLI A2A | `triage my inbox` |

---

## Pre-flight checklist

- [ ] From repo root, run `cd src && uv sync` or `uv --directory src sync`; do not run `uv sync` from the repo root unless `pyproject.toml` has moved there.
- [ ] If `uv` warns that the active `VIRTUAL_ENV` does not match `src/.venv`, either deactivate the root venv and use `src/.venv`, or intentionally target the active env with `uv --directory src sync --active`.
- [ ] `cd src && uv run --env-file .env python main.py --agent base` boots clean.
- [ ] `cd src && uv run --env-file .env python main.py --agent demo` boots clean.
- [ ] Azure CLI is logged into the tenant/subscription that owns the Foundry project.
- [ ] Work IQ local auth is ready and no browser/device-code prompt appears during rehearsal.
- [ ] Hosted Work IQ settings use `DEM333_WORK_IQ_CLIENT_ID` and **not** `AZURE_CLIENT_ID`.
- [ ] `DEM333_MSAL_CACHE_B64` is current for hosted Work IQ, or direct-token smoke mode is intentionally being used.
- [ ] Hosted agent `dem333-openclaw-agent-stitched` has `responses` and `a2a` protocols enabled.
- [ ] Hosted traffic routes to the intended latest version before the talk.
- [ ] App Insights receives recent `invoke_agent LangGraph` spans with `gen_ai.input.messages` and `gen_ai.output.messages`.
- [ ] `FOUNDRY_A2A_URL` and `FOUNDRY_A2A_AGENT_CARD_PATH=agentCard/v0.3` are exported before running the bridge.
- [ ] Copilot CLI starts with `/tmp/copilot-a2a-bridge.json`, can see `search_agent` and `call_agent_a2a`, and the real A2A inbox-triage prompt succeeds.
- [ ] Browser fallback prompt is ready in case Amazon blocks automation.
- [ ] Terminal font is at least 16pt, line wrapping is on, and secrets/tokens are not visible.

---

## Fast fallback branches

| Risk | What to do live |
|---|---|
| Work IQ auth prompts | Say the local cache expired, show the MCP wiring, then use the hosted smoke result or privacy-safe count prompt. |
| Amazon blocks browser automation | Use the Build session page fallback. The point is the Playwright CLI + Skill pattern, not Amazon. |
| Hosted endpoint is cold | Start the request, explain cold start and the Responses API adapter, then continue with code while it warms. |
| Portal monitoring is slow | Show a prepared App Insights query result with recent `invoke_agent LangGraph` spans and non-empty input/output capture counts. |
| Copilot CLI config fails | Run the direct bridge command; it proves the A2A endpoint and bridge are working even if the CLI session is misconfigured. |

---

## Practice notes

- Keep the spoken thesis tight: **open-source agent code plus Foundry production surfaces**.
- Avoid saying "A2A is MCP." Say: **A2A is the remote agent protocol; MCP is the local adapter Copilot CLI can load for this demo.**
- Keep mailbox outputs privacy-safe unless using a seeded demo mailbox.
- Do not dwell on deployment CLI details during the talk. The audience needs to understand the adapter and production surface, not watch a container build.
- In observability, point at three concrete spans: `invoke_agent LangGraph`, `model`, and `tools`.
- If you are running long, cut the browser primary prompt and use the Build session page fallback.
