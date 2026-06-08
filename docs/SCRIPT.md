# DEM333 - Demo Script

**Session:** How Foundry Integrates With Open Source Frameworks and Tools
**Speakers:** **Facundo** (narrator / asks the questions) and **Nagkumar** (drives VS Code, terminal, and Foundry)
**Duration target:** 30 minutes
**Demo project:** `src/` - a homegrown "OpenClaw-style" agent built with LangGraph, MCP, Skills, Playwright, and Microsoft Foundry.

## Story in one sentence

We start with ordinary open-source agent code, progressively add real tools and skills, then move the same LangGraph agent into Foundry so it can be invoked through the Responses API, observed with OpenTelemetry, and called by another agent through A2A.

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

## 1. Hook - why this matters - 3 min

*(stage) Title slide is up. Camera on both speakers.*

**F:** Hi everyone! Welcome to **How Foundry Integrates With Open Source Frameworks and Tools**. My name is Facundo and today... I'm joined by Nagkumar who is going to drive the keyboard.

**F:** Today's question is simple: if you already have an agent build with open-source technologies, how do you move it to production without rewriting it?

*(stage) Switch to a single slide: "Goal: build our own OpenClaw using only open-source pieces, then graduate it to Foundry."*

**F:** And for that, we brought an interesting setup. I'm sure are all familiar with *OpenClaw*: this general purpose agent that has access to your computer, can browse the web, read email, and what not. So today... we are going to **build our own OpenClaw, live**, using open-source frameworks and tools.

*(stage) Slide: "Open-source agent code -> real tools -> hosted in Foundry -> observable -> callable by other agents.")*

**F:** And then...we are going to show how **Microsoft Foundry takes that exact same code and supercharges it**. Sounds fun? Let's get started.

---

## 2. Minimal agent loop in LangGraph - 3 min

**F:** So, let's start at the bottom. If I want to build an agent today - no Foundry, no platform magic - what's the smallest amount of code I need?

*(stage) Open `src/dem333/agent_base.py`.)*

**N:** At the core, we need a model and an agent loop. The agent loop is what keeps the agent moving: it asks the model for the next step, runs tools when needed, and uses each result to decide what happens next. This file is intentionally small. The model comes from LangChain's `init_chat_model`, and the loop is built with `create_deep_agent`.

**N:** The important point is that this is ordinary LangChain/LangGraph-style code. Most Foundry models expose OpenAI-compatible APIs, so LangChain can talk to a Foundry model deployment using the protocol it already understands. Changing the model target is configuration, not a rewrite.

**F:** So in this case, LangChain owns the agent loop, and Foundry provides the model via the OpenAI-compatible protocol.

**N:** Right. I'll run the smallest local agent first. It takes a few seconds to boot, so while it starts, watch for the DEM333 banner and notice that this is still just local Python - no hosted endpoint yet.

---

## 3. First interaction in the console - 1.5 min

*(stage) Open integrated terminal. Venv already active. From repo root, remember the Python project is under `src/`.)*

**Prompt card**

```text
Hello!
```

*(stage) Type the prompt. The DEM333 banner appears, the agent replies with a generic assistant response.)*

And then we can see it replied back.

**F:** This is useful, but it still cannot do work outside the model. One reason agents like OpenClaw are useful is that they can do things. What is the usual pattern for giving an agent tools?

---

## 4. Tools via MCP - connecting Work IQ Mail - 4.5 min

**N:** The open-source pattern is MCP - Model Context Protocol. MCP is an open protocol that lets an agent discover tools and call them. For this demo, the MCP server is **Work IQ Mail**, which gives the agent access to Microsoft 365 mail capabilities through a tool interface.

**N:** The agent does not need to know every HTTP endpoint in Microsoft 365. It connects to the Work IQ MCP server, asks for tools, and receives tool schemas like search messages, get message details, draft replies, and so on.

*(stage) Open `src/dem333/agent_mcp.py` and highlight the MCP client wiring.)*

```python
connections: dict[str, Any] = {"mail": build_work_iq_mail_connection()}
return MultiServerMCPClient(connections)
```

**N:** Then we pass the discovered MCP tools into the same agent loop:

```python
mcp_tools = await mcp_client.get_tools()
return configure_mcp_tool_error_handling(mcp_tools)
```

**F:** So you're saying I can take *any* LangGraph agent I already have, and just plug this server over the open protocol to give it access to Work IQ?

**N:** Exactly. I'll restart with the MCP-enabled agent now. The next request may pause while the tool connection is established, so while it runs, watch for tool discovery and the Work IQ / Mail MCP call rather than just the final text.

*(stage) Restart with the MCP-enabled agent.)*

**Prompt card - privacy-safe for rehearsal**

```text
check my email
```

*(stage) The spinner shows Work IQ / Mail MCP tool calls. The final answer should be compact and privacy-safe.)*

**N:** While that spinner is moving, watch the tool boundary. The agent discovered the mail tools at runtime and chose the right one. We are also keeping the output privacy-safe.

**N:** Now the same local agent can call Microsoft 365 through MCP. The tool boundary is open and inspectable, and the agent still remains normal Python code.

---

## 5. Skills - teaching the agent how to use tools - 4 min

**F:** So the agent now has hands, but we want more than that... "get my unread email" is not that useful, what's useful is something like "triage my inbox", that saves me time. Do I need to tell it every step?

**N:** That's where Skills come in. Tools are verbs like "search messages." A Skill is a playbook like "triaging inbox", which should pull minimal fields first, classify into categories, assign priority,  and draft only when asked."

**N:** Now I'll restart with the Skills-enabled agent and ask it to triage my inbox.

**Prompt card**

```text
triage my inbox
```

**F:** Ohh nice, we can already see the agent picked up the triage skill. How did we created the skill and how the agent found it?

*(stage) Open `src/dem333/skills/inbox-triage/SKILL.md`.)*

**N:** Here we have a triage Skill: a markdown playbook with a small frontmatter block. No special service. No proprietary schema. The agent reads it only when the prompt is relevant.

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

**N:** Let's go back to the terminal and see the output. We see the agent has assign proiorities to each of the emails, and gives me a summary of what needs inmediate action and what not.

**F:** That's bold. Same model, same tools — but totally different behavior because of the reusable skill.

**N:** That's the big point. Skills are a lightweight way to make agent behavior repeatable without turning every instruction into a massive system prompt.

---

## 6. Sophisticated tools - Playwright browser - 4 min

**F:** The other thing people expect from OpenClaw is the ability to browse the web. What is the open-source pattern there?

*(stage) Open `src/dem333/skills/web-browsing/SKILL.md`, then `src/dem333/tools/browser.py`.)*

**N:** For that, we can use Playwright, an open-source framework that allows developers (and agents) to control browsers using a single API. Here we use `@playwright/cli`: one command-line tool, plus a Skill that teaches the agent the command vocabulary.

Our get_tools method now has an added playright_cli tool.

*(stage) Open final agent `src/dem333/agent.py` and highlight that both Work IQ tools and `playwright_cli` are returned.)*

```python
return configure_mcp_tool_error_handling(mcp_tools) + [playwright_cli]
```

**N:** Let's run it again with tool and give it a task, let's say, find a nice coffee cup on amazon.com

**Prompt card - primary**

```text
Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find.
```

**F:** While this runs, I'm wondering - why did we use a different approach here compared to the MCP server from Work IQ?

**N:** We could use an MCP server, but browser work can create a large tool surface. Here the command line is simpler. The Python tool has one `args` string and an optional browser session. Snapshots and command details only enter the context when the agent asks for them.

**F:** Got it. So it is easier for the model, and it is more token efficient. The result is back now, and the browser flow is the proof.

**F:** While the browser steps run, notice that the model did not receive a giant browser API surface. It chose the Web Browsing Skill, then drove one Playwright CLI tool through a sequence of small commands and snapshots.

---

## 7. From console to cloud - Foundry Responses API - 3 min

**F:** Now, fair question from the audience: this is running in a terminal, but production users are not going to SSH your laptop, right?. How do we take this to production? What's our deployment story here?

*(stage) Open `src/server.py`.)*

**N:** This is where Foundry steps in. Foundry hosts the same LangGraph agent and exposes it through an OpenAI-compatible Responses API. This file is the adapter layer. Notice that we still call the same `build_agent()` from `dem333.agent`.

**N:** There are two details worth calling out:

1. `ResponsesHostServer` exposes the LangGraph agent as a Responses-compatible endpoint.
2. We initialize the Foundry server host before building the graph so OpenTelemetry/LangChain instrumentation can attach before the graph is constructed.

**F:** So if I'm reading this correctly, you are just wrapping the agent in the protocol with this server. So the same code path can run locally in the console or remotely, right?

**N:** Correct. For the talk, the agent is already deployed as `dem333-openclaw-agent-stitched`.

**N:** I'll send the same triage prompt to the hosted agent next. Hosted calls can take a moment if the container is warming, so while it runs, I'll call out that this is the same `build_agent()` path now reached through the Responses API.

**Prompt card**

```text
triage my inbox
```

*(stage) Send the hosted smoke prompt through the endpoint or Foundry playground.)*



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

**N:** The content capture is intentional for this demo but In a real production rollout, decide this based on your organization's privacy and data retention policy.


**F:** And OpenTelemetry with semantic conventions means the data uses an industry standard. It can be read with any tool. No vendor lock-in, just data.

---

## 9. A2A - calling the hosted agent from Copilot CLI - 2 min

**F:** Last question. They say that 2026 is all about agents working with other agents, can another agent call this one?

**N:** Yes. One of the most interesting thing of hosting the agent in Foundry is that I get an A2A endpoint that another A2A-compatible client can use to discover the agent card and send messages to the hosted agent.

**N:** Let's see how this looks like in Copilot CLI. I have it open here, and let's ask it to triage my inbox now.

**Prompt card - inside Copilot CLI**

```text
triage my inbox
```

**N:** So now, how does this work? We exposed a tiny local A2A directory as an MCP server with 2 tools:

- search_agent
- call_a2a_agent

that Copilot can use to search in an agent directory we configured and then call them via the A2A protocol.

*(stage) Open `src/dem333/a2a/__main__.py` and highlight the tools.)*

**N:** Let's go back to the terminal and see what Copilot found. Copilot searched for the agent and then called it via A2A which will perform the task.

**F:** Pause on what just happened. Copilot CLI, a totally different agent runtime, searched an A2A directory exposed as MCP, finds the agent, it uses A2A to reach our LangGraph agent hosted in Foundry, which then used Work IQ MCP server, applied a skill, and answered. That's the beaty of this because **None of those pieces had to know about each other.**.

---

## 10. Wrap-up - 1.5 min

*(stage) End slide with QR code / repo URL.)*

**F:** That's the power of the open-source story. And that's the story we want you to take from this session.

I think it's a wrap, thank you everyone, code is available on GitHub so you can take a look to see what we did. 

We'll stick around for questions.

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
- [ ] Hosted Work IQ settings use `WORK_IQ_CLIENT_ID` and **not** `AZURE_CLIENT_ID`.
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
