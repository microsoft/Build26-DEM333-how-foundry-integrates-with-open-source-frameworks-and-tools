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

**F:** Hi everyone! Welcome to **How Foundry Integrates With Open Source Frameworks and Tools**. My name is Facundo and today... I'm joined by Nagkumar who is going to drive the demo.

**F:** Today's question is simple: if your agent already exists in LangGraph, MCP, or plain Python, how do you move it to production without rewriting it?

**F:** To demostrate this, we broght you an interesting setup. I'm sure you are all familiar with OpenClaw right? This We'll build an OpenClaw-style agent from developer-native pieces, then show where Foundry adds the production layer: hosting, observability, and agent-to-agent access.

*(stage) Switch to a single slide: "Goal: build our own OpenClaw using only open-source pieces, then graduate it to Foundry."*

**F:** And for that... we broght to you an interesting setup. You've all seen *OpenClaw*, right? — this general-purpose agent that can browse the web, read your email, and what not. So today, we are going to **build our own OpenClaw, live**, using open-source frameworks and tools — and then..."

*(stage) Slide: "Open-source agent code -> real tools -> hosted in Foundry -> observable -> callable by other agents.")*

"we are going to show how **Microsoft Foundry takes that exact same code and supercharges it**. Sounds fun? Let's get started.

---

## 2. Minimal agent loop in LangGraph - 3 min

**F:** Nagku, start at the bottom. If I want to build an agent today - no hosting, no platform magic - what's the smallest amount of code I need?

*(stage) Open `src/dem333/agent_base.py`.)*

**N:** At the core, we need a model and an agent loop. [[FACUNDO COMMENT: YOU MAY NEED TO BRIEFLY MENTION WHAT'S AN AGENT LOOP]]. This file is intentionally small. The model comes from LangChain's `init_chat_model`, and the loop is built with `create_deep_agent`.

*(stage) Highlight the core lines.)*

```python
model = init_chat_model("openai:gpt-5.2")

return create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)
```

**N:** The important point is that this is ordinary LangChain/LangGraph-style code. Foundry is not in this file. The model configuration comes from environment variables, so the same code can point at a Foundry model deployment without changing the agent loop. [[FACUNDO COMMENT: I THINK WE NEED TO MENTION THAT MOST MODELS IN FOUNDRY USES OPENAI COMPATIBLE APIS.]]

**F:** So in this case, LangChain owns the agent loop, and Foundry provides the model via the OpenAI-compatible protocol.

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

**F:** Indeed. One of the things that make OpenClaw so popular is its ability to do things. What's the typical pattern to give access to tools?
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
return configure_work_iq_tool_error_handling(mcp_tools)
```

**F:** So you're saying I can take *any* LangGraph agent I already have, and just plug this server over the open protocol?

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

**F:** This is great. So the agent now has hands — but we want more than that. Check my email doesn't save me time. For example, triaging my inbox does that. Do I need to ask it to open each message, read the content, etc?

**N:** That's where Skills come in. A tool is a verb: "search messages." A Skill is a playbook: "when triaging inbox, pull minimal fields first, classify into categories, assign P0-P3 priority, avoid exposing private message content, and draft only when asked."

*(stage) Open `src/dem333/skills/inbox-triage/SKILL.md`.)*

**N:** A Skill is just a markdown file with a small frontmatter block. No special service. No proprietary schema. The agent reads the skill only when the prompt is relevant.

*(stage) Restart with the skills-enabled agent.)*

```bash
uv run python main.py --agent skills
```

**Prompt card**

```text
Triage my inbox. Use the inbox triage skill. Do not include senders, subjects, body text, or personal data. Return only priority counts P0-P3, category counts, and whether drafts are recommended.
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

**F:** That's bold. Same model, same tools — but totally different behavior because of the resuable skill.

**N:** That's the big point. Skills are a lightweight way to make agent behavior repeatable without turning every instruction into a massive system prompt.

---

## 6. Sophisticated tools - Playwright browser - 4 min

**F:** The other thing people expect from an OpenClaw-style agent is browser work. What is the open-source pattern there?

*(stage) Open `src/dem333/skills/web-browsing/SKILL.md`, then `src/dem333/tools/browser.py`.)*

**N:** For that, we can use Playwright, an open-source framework that allows developers (and agents) to control browsers using a single API. Here we use `@playwright/cli`: one command-line tool, plus a Skill that teaches the agent the command vocabulary.

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

**F:** While this runs, I'm wondering - why did we use a different approach here compared to the MCP server from Work IQ?

**N:** We could use an MCP server. However, that would create long instructions with the MCP server details that go to the context window. A more efficient approch these days is to use the command line. The Python tool schema stays tiny - one `args` string and an optional browser session. The page snapshots and command details only enter the context when the agent asks for them.

**F:** Got it. So this is not only easier to use for the model, it's also more token efficient. Ok, it's back now. 15 dolars for an xbox mug? It better be nice!

**Prompt card - safer fallback**

```text
Open https://build.microsoft.com/en-US/sessions/DEM333 and summarize the session in 3 bullets.
```

*(stage) Spinner should show `skill: Web Browsing`, then `playwright_cli` commands such as `open`, `snapshot`, `type`, `press`, and `click`.)*

**F:** The important part is not Amazon. The important part is that the agent selected the browser skill, used a single powerful tool safely, and kept the browser state across steps.

**N:** Exactly. For live demos, public websites can block automation, so the fallback is the Build session page. The story still lands because the tool pattern is the same.

---

## 7. From console to cloud - Foundry Responses API - 3 min

**F:** Now, fair question from the audience: this is all running in a terminal, but nobody wants production users SSH-ing into your laptop. How can we take this to production?

*(stage) Open `src/server.py`.)*

**N:** This is where Foundry can step in again. Foundry can hosts the same LangGraph agent and expose it behind the OpenAI-compatible Responses API. This file is the adapter layer. Notice that we still call the same `build_agent()` from `dem333.agent`.

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

**F:** If I'm reading this correctly, you are wrapping the agent. So the same code path can run locally in the console or remotely, right?

**N:** Correct. For the talk, the agent is already deployed as `dem333-openclaw-agent`. If we need to show the deployment path, the runbook is in `docs/HOSTED_AGENT_DEPLOYMENT.md`.

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

**F:** Ok. We got the agent to the cloud. The next production question is: can we see what it is doing?

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

**F:** That's the kind of detail you need to have confidence to move something to production.

**Prompt card - generate trace traffic**

```text
In one sentence, say this request is generating DEM333 OpenTelemetry input and output capture traffic.
```

**Fallback:** If the portal view is slow, use a prepared App Insights query result that shows recent `invoke_agent LangGraph` rows with non-empty input and output capture counts.

---

## 9. A2A - calling the hosted agent from Copilot CLI - 2.5 min

**F:** Last question. They say that 2026 is all about agents working with other agents, can another agent call this one?

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

**F:** Pause on what just happened. So Copilot CLI, a totally different agent runtime, called an MCP tool. That tool used A2A to reached our LangGraph agent hosted in Foundry, which then used Work IQ MCP server, applied a skill, and answered. **None of those pieces had to know about each other.** Impressive.

**N:** And I'll give you something extra. The trace now follows that handoff. In App Insights, the local bridge span `invoke_agent dem333_foundry_a2a` and the hosted `invoke_agent LangGraph` span share the same operation ID, so we can explain both interop and observability in one screen.

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
