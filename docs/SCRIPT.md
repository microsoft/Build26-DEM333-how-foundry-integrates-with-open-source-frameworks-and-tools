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
7. A2A lets Copilot CLI reach the hosted agent through a small local MCP bridge.

> **Conventions**
>
> - **F:** Facundo speaking.
> - **N:** Nagkumar speaking.
> - *(stage)* Action on screen or hand-off cue.
> - **Prompt card:** Exact prompt to type during rehearsal.
> - **Fallback:** What to say or do if a live service is slow.

---

## Current demo state to reflect during rehearsal

- The main final agent is `src/dem333/agent.py`.
- The hosted agent name is `dem333-openclaw-agent`.
- The hosted endpoint is enabled for both `responses` and `a2a`.
- The currently rehearsed hosted deployment routes to version 6; verify before going on stage because this can change after redeploys.
- Work IQ uses `DEM333_WORK_IQ_CLIENT_ID` / `WORK_IQ_CLIENT_ID`; do **not** put the Work IQ public-client app ID in `AZURE_CLIENT_ID` for hosted deployments.
- The Copilot CLI integration is `dem333.copilot_a2a_bridge`.
- A2A is not a wrapper around MCP. A2A is how another agent discovers and calls our hosted agent. The local MCP bridge exists only because Copilot CLI can consume MCP tools today.

---

## 1. Hook - why this matters - 3 min

*(stage) Title slide is up. Camera on both speakers.*

**F:** Welcome. I'm Facundo, and this is **How Foundry Integrates With Open Source Frameworks and Tools**. Nagkumar is going to drive the demo.

**F:** Today's question is simple: if your agent already exists in LangGraph, MCP, or plain Python, how do you move it to production without rewriting it?

*(stage) Slide: "Open-source agent code -> real tools -> hosted in Foundry -> observable -> callable by other agents.")*

**F:** We'll build an OpenClaw-style agent from developer-native pieces, then show where Foundry adds the production layer: hosting, observability, and agent-to-agent access.

**F:** I'll frame each layer. Nagkumar will keep the code moving.

**F:** The punchline is: **bring your agent, keep your framework, and let Foundry provide the production surface around it.**

**N:** Let's start with the smallest useful agent and add one capability at a time.

---

## 2. Minimal agent loop in LangGraph - 3 min

**F:** Nagku, start at the bottom. If I want to build an agent today - no hosting, no platform magic - what is the smallest useful shape?

*(stage) Open `src/dem333/agent_base.py`.)*

**N:** At the core, we need a model and an agent loop. This file is intentionally small. The model comes from LangChain's `init_chat_model`, and the loop is built with `create_deep_agent`.

*(stage) Highlight the core lines.)*

```python
model = init_chat_model("openai:gpt-5.2")

return create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)
```

**N:** The important point is that this is ordinary LangChain/LangGraph-style code. Foundry is not in this file. The model configuration comes from environment variables, so the same code can point at a Foundry model deployment without changing the agent loop.

**F:** So the framework owns the loop, and Foundry can still provide the model behind the standard OpenAI-compatible surface.

**N:** Right. Now let's run it locally.

---

## 3. First interaction in the console - 1.5 min

*(stage) Open integrated terminal. Venv already active. From repo root, remember the Python project is under `src/`.)*

```bash
cd src
uv run python main.py --agent base
```

**Prompt card**

```text
Hello! In one sentence, tell me what you can help with.
```

*(stage) The DEM333 banner appears, the agent replies with a generic assistant response.)*

**N:** This is useful, but it's still only a brain. If I ask it to read my email, it doesn't have any hands.

**F:** And that is where open-source agents become interesting: tools.

---

## 4. Tools via MCP - connecting Work IQ Mail - 4.5 min

**F:** How do we give this agent real capabilities without hard-coding one-off integrations?

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
return configure_work_iq_tool_error_handling(mcp_tools)
```

**F:** So if I already have a LangGraph agent, I can add an MCP server without adopting a new platform SDK.

**N:** Exactly. Let's show the difference.

*(stage) Restart with the MCP-enabled agent.)*

```bash
uv run python main.py --agent mcp
```

**Prompt card - privacy-safe for rehearsal**

```text
Check my inbox using Work IQ Mail. Do not include senders, subjects, body text, or personal data. Reply only in this format: INBOX_CHECK_OK=yes; MESSAGE_COUNT=<number>.
```

*(stage) The spinner shows Work IQ / Mail MCP tool calls. The final answer should be compact and privacy-safe.)*

**N:** Now the same local agent can call Microsoft 365 through MCP. The tool boundary is open and inspectable, and the agent still remains normal Python code.

**Fallback:** If auth expires or mail is slow, say: "This is why we preflight Work IQ before going on stage. The important artifact is that the agent discovered and attempted the MCP mail tool; the hosted version is already validated, so we'll continue with the prepared flow."

---

## 5. Skills - teaching the agent how to use tools - 4 min

**F:** Tools give the agent verbs. But if I ask for "triage my inbox," I don't want it randomly deciding what triage means every time.

**N:** That's where Skills come in. A tool is a verb: "search messages." A Skill is a playbook: "when triaging inbox, pull minimal fields first, classify into categories, assign P0-P3 priority, avoid exposing private message content, and draft only when asked."

*(stage) Open `src/dem333/skills/inbox-triage/SKILL.md`.)*

**N:** A Skill is just a markdown file with a small frontmatter block. No special service. No proprietary schema. The agent reads the skill only when the prompt is relevant.

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

*(stage) Restart with the skills-enabled agent.)*

```bash
uv run python main.py --agent skills
```

**Prompt card**

```text
Triage my inbox. Use the inbox triage skill. Do not include senders, subjects, body text, or personal data. Return only priority counts P0-P3, category counts, and whether drafts are recommended.
```

*(stage) Watch for the skill load notice and Work IQ tool calls.)*

**F:** Same model and same MCP server, but now the behavior is more consistent because the instructions are packaged as a reusable skill.

**N:** That's the big point. Skills are a lightweight way to make agent behavior repeatable without turning every instruction into a massive system prompt.

---

## 6. Sophisticated tools - Playwright browser - 4 min

**F:** The other thing people expect from an OpenClaw-style agent is browser work. What is the open-source pattern there?

*(stage) Open `src/dem333/skills/web-browsing/SKILL.md`, then `src/dem333/tools/browser.py`.)*

**N:** We could expose a browser through many MCP tools, but that creates a large tool surface. Here we use Microsoft `@playwright/cli`: one command-line tool, plus a Skill that teaches the agent the command vocabulary.

**N:** The Python tool schema stays tiny - one `args` string and an optional browser session. The page snapshots and command details only enter the context when the agent asks for them.

*(stage) Open final agent `src/dem333/agent.py` and highlight that both Work IQ tools and `playwright_cli` are returned.)*

```python
return configure_work_iq_tool_error_handling(mcp_tools) + [playwright_cli]
```

*(stage) Run the final local demo agent.)*

```bash
uv run python main.py --agent demo
```

**Prompt card - primary**

```text
Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find. Do not sign in, add anything to cart, or attempt checkout. If the site blocks browsing, say it was blocked.
```

**Prompt card - safer fallback**

```text
Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.
```

*(stage) Spinner should show `skill: Web Browsing`, then `playwright_cli` commands such as `open`, `snapshot`, `type`, `press`, and `click`.)*

**F:** The important part is not Amazon. The important part is that the agent selected the browser skill, used a single powerful tool safely, and kept the browser state across steps.

**N:** Exactly. For live demos, public websites can block automation, so the fallback is the Build session page. The story still lands because the tool pattern is the same.

---

## 7. From console to cloud - Foundry Responses API - 3 min

**F:** This is great locally, but nobody wants production users SSH-ing into your laptop. How does Foundry help without forcing us to rewrite the agent?

*(stage) Open `src/server.py`.)*

**N:** Foundry hosts the same LangGraph agent behind the OpenAI-compatible Responses API. This file is the adapter layer. Notice that we still call the same `build_agent()` from `dem333.agent`.

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

**F:** So the same code path can run locally in the console or remotely through an API that existing OpenAI SDK clients already understand.

**N:** Yes. For the talk, the agent is already deployed as `dem333-openclaw-agent`. If we need to show the deployment path, the runbook is in `docs/HOSTED_AGENT_DEPLOYMENT.md`.

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
In one sentence, explain why the Foundry Responses API can host this LangGraph agent without rewriting it.
```

**Fallback:** If the live API is slow, switch to the Foundry playground for the same agent and say: "The protocol is the same; the playground is just another client of the hosted agent."

---

## 8. Observability - OpenTelemetry and App Insights - 3 min

**F:** Once the agent is in the cloud, the next production question is: can we see what it is doing?

**N:** Yes. Foundry integrates with Application Insights and OpenTelemetry. The demo uses the Microsoft OpenTelemetry distro and GenAI semantic conventions, so we can inspect the LangGraph span, model calls, tool calls, latency, and captured input/output.

*(stage) Open Foundry monitoring or App Insights traces for `dem333-openclaw-agent`.)*

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

**F:** This is the production value. We didn't just host an agent. We gained the operational view: what ran, what tools were called, how long it took, and where failures would show up.

**Prompt card - generate trace traffic**

```text
In one sentence, say this request is generating DEM333 OpenTelemetry input and output capture traffic.
```

**Fallback:** If the portal view is slow, use a prepared App Insights query result that shows recent `invoke_agent LangGraph` rows with non-empty input and output capture counts.

---

## 9. A2A - calling the hosted agent from Copilot CLI - 2.5 min

**F:** Last question. If 2026 is all about agents working with other agents, can another agent call this one?

**N:** Yes. Once the Foundry A2A endpoint is enabled, another A2A-compatible client can discover the agent card and send messages to the hosted agent.

**N:** For Copilot CLI specifically, the current integration point is MCP tools. So we expose a tiny local MCP bridge that calls the Foundry A2A endpoint. That does **not** mean A2A is MCP. It means MCP is the local adapter Copilot CLI can load today.

*(stage) Open `src/dem333/copilot_a2a_bridge.py` and highlight the tool.)*

```python
@mcp.tool()
async def ask_dem333_agent(message: str, ctx: Context) -> str:
    """Ask the DEM333 Foundry hosted agent through its A2A endpoint."""
    return await invoke_foundry_a2a(message, ctx)
```

*(stage) Direct bridge smoke test.)*

```bash
cd src
export FOUNDRY_A2A_URL="${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/a2a"
export FOUNDRY_A2A_AGENT_CARD_PATH="agentCard/v0.3"
export APPLICATIONINSIGHTS_CONNECTION_STRING="${APPLICATION_INSIGHTS_CONNECTION_STRING}"

uv run python -m dem333.copilot_a2a_bridge --message "Reply exactly A2A bridge ready."
```

*(stage) Then start Copilot CLI with the bridge.)*

```bash
cat > /tmp/copilot-a2a-bridge.json <<JSON
{
  "mcpServers": {
    "copilot-a2a-bridge": {
      "command": "uv",
      "args": ["--directory", "$PWD", "run", "python", "-m", "dem333.copilot_a2a_bridge"],
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
Use the ask_dem333_agent tool to ask: check my inbox using Work IQ Mail and return only priority/category labels and a total message count. Do not include senders, subjects, body text, or personal data.
```

*(stage) Copilot CLI calls the MCP bridge; the bridge invokes the Foundry A2A endpoint; the hosted LangGraph agent uses Work IQ MCP and Skills; the answer appears back in Copilot CLI.)*

**F:** Pause on what happened. Copilot CLI, a different agent runtime, called an MCP tool. That tool crossed into A2A. A2A reached our LangGraph agent hosted in Foundry. That agent then used another MCP server, Work IQ Mail, and applied a Skill. None of these pieces had to be built into one monolith.

**N:** And the trace now follows that handoff. In App Insights, the local bridge span `invoke_agent dem333_foundry_a2a` and the hosted `invoke_agent LangGraph` span share the same operation ID, so we can explain both interop and observability in one screen.

**N:** That is the open-source integration story: framework, tools, skills, hosting, telemetry, and agent-to-agent interoperability.

---

## 10. Wrap-up - 1.5 min

*(stage) End slide with QR code / repo URL.)*

**F:** Today we started with open-source agent code, added real tools, gave it reusable behavior with Skills, hosted it in Foundry, observed it with OpenTelemetry, and called it from another agent through A2A.

**F:** The takeaway is simple: Foundry does not replace the frameworks developers already use. It gives them the production surface around those agents.

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
| 9. A2A from Copilot CLI | 2:30 | 28:30 |
| 10. Wrap-up / Q&A buffer | 1:30 | 30:00 |

---

## Rehearsal prompt cards

Use these exact prompts when practicing so the telemetry and stage flow are predictable.

| Demo beat | Prompt |
|---|---|
| Base console | `Hello! In one sentence, tell me what you can help with.` |
| Work IQ MCP | `Check my inbox using Work IQ Mail. Do not include senders, subjects, body text, or personal data. Reply only in this format: INBOX_CHECK_OK=yes; MESSAGE_COUNT=<number>.` |
| Inbox skill | `Triage my inbox. Use the inbox triage skill. Do not include senders, subjects, body text, or personal data. Return only priority counts P0-P3, category counts, and whether drafts are recommended.` |
| Browser primary | `Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find. Do not sign in, add anything to cart, or attempt checkout. If the site blocks browsing, say it was blocked.` |
| Browser fallback | `Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.` |
| Hosted Responses | `In one sentence, explain why the Foundry Responses API can host this LangGraph agent without rewriting it.` |
| Telemetry | `In one sentence, say this request is generating DEM333 OpenTelemetry input and output capture traffic.` |
| Direct A2A | `Reply exactly A2A bridge ready.` |
| Copilot CLI A2A | `Use the ask_dem333_agent tool to ask: check my inbox using Work IQ Mail and return only priority/category labels and a total message count. Do not include senders, subjects, body text, or personal data.` |

---

## Pre-flight checklist

- [ ] From repo root, run `cd src && uv sync` or `uv --directory src sync`; do not run `uv sync` from the repo root unless `pyproject.toml` has moved there.
- [ ] If `uv` warns that the active `VIRTUAL_ENV` does not match `src/.venv`, either deactivate the root venv and use `src/.venv`, or intentionally target the active env with `uv --directory src sync --active`.
- [ ] `cd src && uv run python main.py --agent base` boots clean.
- [ ] `cd src && uv run python main.py --agent demo` boots clean.
- [ ] Azure CLI is logged into the tenant/subscription that owns the Foundry project.
- [ ] Work IQ local auth is ready and no browser/device-code prompt appears during rehearsal.
- [ ] Hosted Work IQ settings use `DEM333_WORK_IQ_CLIENT_ID` and **not** `AZURE_CLIENT_ID`.
- [ ] `DEM333_MSAL_CACHE_B64` is current for hosted Work IQ, or direct-token smoke mode is intentionally being used.
- [ ] Hosted agent `dem333-openclaw-agent` has `responses` and `a2a` protocols enabled.
- [ ] Hosted traffic routes to the intended latest version before the talk.
- [ ] App Insights receives recent `invoke_agent LangGraph` spans with `gen_ai.input.messages` and `gen_ai.output.messages`.
- [ ] `FOUNDRY_A2A_URL` and `FOUNDRY_A2A_AGENT_CARD_PATH=agentCard/v0.3` are exported before running the bridge.
- [ ] `uv run python -m dem333.copilot_a2a_bridge --message "Reply exactly A2A bridge ready."` succeeds.
- [ ] Copilot CLI starts with `/tmp/copilot-a2a-bridge.json` and can see the `ask_dem333_agent` tool.
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
