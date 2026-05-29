# DEM333 — Demo Script

**Session:** How Foundry Integrates With Open Source Frameworks and Tools
**Speakers:** **Facundo** (narrator / asks the questions) · **Nagkumar** (drives VS Code, shares screen)
**Duration target:** 30 minutes
**Demo project:** `src/` — a "homegrown OpenClaw" built with LangGraph + Foundry

> **Conventions used below**
> - **F:** = Facundo speaking
> - **N:** = Nagkumar speaking
> - *(stage)* = action on screen / hand-off cue
> - ⏱ = approximate timing budget so we hit the 30-minute mark

---

## 1. Introduction — ⏱ 2 min

*(stage) Title slide is up. Camera on both speakers.*

**F:** Welcome everyone! I'm Facundo, Principal Product Manager at Microsoft Foundry and today we are going to show you *How Foundry Integrates With Open Source Frameworks and Tools*. For that, I'm joined by Nagkumar, Senior Software Engineer at Microsoft Foundry and one of our top contributors to OpenSource who is going to drive the keyboard today.

**F:** So... Quick show of hands — how many of you have already built an agent with an open-source framework like Microsoft Agent Framework, LangChain, or LangGraph? *(pause)* … And how many of you have looked at Microsoft Foundry and wondered "how will this fit here?" That second question is what this session is about.

---

## 2. Objective — Let's build our own OpenClaw — ⏱ 2 min

*(stage) Switch to a single slide: "Goal: build our own OpenClaw using only open-source pieces, then graduate it to Foundry."*

**F:** And for that... we broght to you an interesting setup. You've all seen *OpenClaw*, right? — a general-purpose agent that can browse the web, read your email, remember you, and stalk your significant other online. Today, we are going to **build our own OpenClaw, live**, using open-source frameworks and tools — and then we are going to show how **Microsoft Foundry takes that exact same code and supercharges it**. Sounds fun? Let's get started.

---

## 3. A minimal agent loop in LangGraph — ⏱ 3 min

**F:** Nagku, let's start at the bottom. If I want to build an agent today — no Foundry, no magic — what's the smallest amount of code I need?

*(stage) **N** opens [src/dem333/agent_base.py](src/dem333/agent_base.py) in VS Code.*

**N:** To create a minimal agent you need 2 things: a model and a continuous loop. So let's see an example using LangChain. For the model, we use `init_chat_model` to grab any model — here it's pointing to a GPT model. For the loop, `create_deep_agent` gives us an agent loop that will wait for my inputs and generate an output.

*(stage) Highlight these lines:*

```python
model = init_chat_model("openai:gpt-5.2")
return create_deep_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)
```

**F:** And from where that model is coming from?

**N:** The `init_chat_model` method automatically reads my environment variables and find the model from a Microsoft Foundry project I have setup. Most Foundry Models implement OpenAI Responses API so you can change it if needed to, for example, a DeepSeek model. 

**F:** And what runs that loop?

---

## 4. First interaction in the console — ⏱ 1.5 min

*(stage) **N** opens the integrated terminal. Venv already active.*

**N:** I built a console terminal to execute the loop so we can see things more interactively. Let's just run it.

```bash
cd src
uv run python main.py --agent base
```

*(stage) The DEM333 banner shows up. **N** types:*

> ` Hello! What are you working on today—want help with something specific (writing, coding, planning, troubleshooting), or just exploring an idea?  `

*(stage) Agent replies with a generic "I'm a helpful assistant…" message.*

**F:** Cool — so we have a working loop. Now, one of the reasons OpenClaw is so popular is because it can do things for you, what can this one do for us?

**N:** Not much. If I ask it to read my email, it'll just apologize. Let's give it a hand.

---

## 5. Tools via MCP — connecting Work IQ — ⏱ 4 min

**N:** Let's give it a hand.

The open-source pattern for that connecting the agent to an **MCP Server — Model Context Protocol**. In one sentence: MCP is an open standard that lets an agent discover and call tools to perform actions. 

And one of the most powerful MCP servers out there today is **Work IQ** — a first-party server from Microsoft that gives an agent access to **everything in Microsoft 365**: email, calendar, contacts, files, Teams messages, the lot. So let's give this agent access to my email.

*(stage) **N** opens [src/dem333/tools/work_iq.py](src/dem333/tools/work_iq.py).*

**N:** From the agent's point of view, Work IQ is just an MCP endpoint we point at. The mail surface exposes tools like `searchMessages`, `getMessage`, `createMessage`, `sendDraft`, and so on.

**N:** And in [agent_mcp.py](src/dem333/agent_mcp.py) we wire it in with the open-source `langchain-mcp-adapters` package — **no Foundry SDK required**:

```python
def get_mcp_client() -> MultiServerMCPClient:
    connections = {"mail": build_work_iq_mail_connection()}
    return MultiServerMCPClient(connections)
```

**F:** So you're saying I can take *any* LangGraph agent I already have, and just plug this server over the open protocol?

**N:** That's the whole point. Let me show it live.

*(stage) **N** restarts with the MCP-enabled agent. Prompt:*

```bash
uv run python main.py --agent mcp
```

> `Check my inbox`

*(stage) The Rich spinner shows the agent calling `mcp_MailTools_graph_mail_searchMessages`. Output is a clean list of 5 messages.*

**F:** Beautiful. So the agent now has hands — but we want more than that. For example, if I want to triage my inbox, do I need to ask it to open each message, read the content, etc?

---

## 6. Skills — teaching the agent *how* to use tools — ⏱ 4 min

**N:** That's where **Skills** come into play. Tools are like a *verb* — "search messages." But an skill is a *playbook* — "here's how you triage an inbox: pull minimal fields first, classify into five categories, score P0–P3, draft replies using these templates, and never fabricate facts." It's a markdown file the agent reads **only when it's relevant**.

*(stage) **N** opens [src/dem333/skills/inbox-triage/SKILL.md](src/dem333/skills/inbox-triage/SKILL.md).*

Skills is an **open format created by Anthropic** — you just write a skill as a **markdown file** with a small frontmatter block. No SDK, no special runtime, no proprietary schema. Any agent that knows the format can load it.

I have an agent with this skill running, let's take a look now:

*(stage) Restart with the skills-enabled agent. Prompt:*

```bash
uv run python main.py --agent skills
```

> `Triage my inbox.`

*(stage) Watch the spinner: skill loads (`skill: Inbox Triage`), then tool calls fire. The agent, pulls minimal fields, classifies, prioritizes, and produces the Priority Queue / Category Summary / Drafts Ready output.*

**F:** While this runs, how is the agent finding these skills we wrote?

**N:** We give the agent **access to the file system** so it can read the skills we wrote. We mount our `dem333/skills` folder under `/skills/`, and the agent can list and read those markdown files on demand.

*(stage) Show the filesystem wiring in [agent_skills.py](src/dem333/agent_skills.py):*

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={"/skills/": FilesystemBackend(root_dir="dem333/skills", virtual_mode=True)},
)
```

**N:** Now, we see the agent came back with the triage of the inbox and it even drafted reply messages for us to send.

**F:** That's bold. Same model, same tools — but totally different behavior.

---

## 7. Sophisticated tools — Playwright browser — ⏱ 4 min

**F:** OK — inbox is covered. The other thing OpenClaw is famous for is **browsing the web**. Nagku, what's our open-source story there?

*(stage) **N** opens [src/dem333/skills/web-browsing/SKILL.md](src/dem333/skills/web-browsing/SKILL.md).*

**N:** We could use an MCP server. However, a more popular approach these days is to use the command line. Microsoft just shipped **`@playwright/cli`** — a command-line wrapper around Playwright designed for agents. Instead of giving the model 40 fine-grained MCP tools (one per browser action), we give it **one tool**: `playwright_cli`, and a **skill** that teaches it the command vocabulary. Same pattern as before — the verbs live in markdown, not in the tool schema. That saves a huge amount of context.

**F:** Can we see it in action? Ask it for example to find the price of something on amazon.

*(stage) Prompt in the agent:*

```bash
uv run python main.py --agent demo
```

> `Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find.`

*(stage) Spinner shows `skill: Web Browsing` loaded, then a sequence of `playwright_cli` calls: `open https://amazon.com`, `snapshot`, `type "microsoft coffee cup"`, `press Enter`, `snapshot`, `click e<n>`, `snapshot`. Final answer cites the URL and the price.*

**N:** Ok, let's see what it does now...

**F:** While this runs, I'm wondering - why did we use a different approach here compared to the MCP server from Work IQ?

**N:** We could use an MCP server. However, a more popular approch these days is to use the command line. Microsoft just shipped **`@playwright/cli`** — a command-line wrapper around Playwright designed for agents. Instead of giving the model 40 fine-grained MCP tools (one per browser action), we give it **one tool**: `playwright_cli`, and a **skill** that teaches it the command vocabulary. Same pattern as before — the verbs live in markdown, not in the tool schema. That saves a huge amount of context.

**F:** Three things to call out: the agent picked the *skill* on its own based on the prompt, it used a *single* tool with a free-form `args` string, and the persistent browser session means the next prompt can keep going from where we left off. That's smart!

---

## 8. From console to cloud — Responses API on Foundry — ⏱ 3 min

**F:** OK Nagku, fair question from the audience: this is all running in a terminal on your laptop. What happens when I want to ship it and share with others? I don't want my customers SSH-ing into your machine.

**N:** This is the part where Foundry shines. Foundry hosts agents behind the **OpenAI Responses API** — same protocol millions of developers already know. We don't rewrite the agent — we wrap it.

*(stage) **N** opens a small `server.py` that takes the same `build_agent(...)` function and exposes it as a Responses-compatible endpoint, then runs:*

**N:** Now anything that speaks the Responses API — the OpenAI SDK, curl, a Next.js app — can call our LangGraph agent. I can run it locally, or I can deploy it to Foundry using the hosted-agent flow.

*(stage) Show terminal to deploy it:*

```bash
cd src
export TAG=custom-openclaw-$(date -u +%Y%m%d%H%M%S)
export IMAGE="${AZURE_CONTAINER_REGISTRY_NAME}.azurecr.io/${HOSTED_AGENT_NAME}:${TAG}"

az acr build \
  --registry "$AZURE_CONTAINER_REGISTRY_NAME" \
  --image "${HOSTED_AGENT_NAME}:${TAG}" \
  --platform linux/amd64 \
  --source-acr-auth-id "[caller]" \
  .

# Then run the `az cognitiveservices agent create` block from
# docs/HOSTED_AGENT_DEPLOYMENT.md with the same $IMAGE.
```

I have this agent already deployed so let's take a look to the playground.

*(stage) Response streams back.*

**F:** Fantastic, because anything that speaks the Responses API — the OpenAI SDK, curl, a Next.js app — can call our LangGraph agent without changing it.

---

## 9. OpenTelemetry

**F:** One more thing... because our agent became a bit sophisticated right. How can we see what this agent is doing in detail?

**N:** Foundry implements OpenTelemetry using Semantic Conventions for GenAI, which is the same stack used across multiple agentic stacks including GitHub Copilot.

It I switch to the Monitoring tab I have access to the traces from this agent.

*(stage) Show the traces.)*

I can see the duration and also check where my agent is spending all the time and tokens.

## 10. A2A — calling our agent from Copilot CLI — ⏱ 2.5 min

**F:** Ok, last question. Because I heard that 2026 is all about agents calling other agents... can other agents talk with this one? Is that a thing?

**N:** Yes — once we enable the Foundry **A2A (Agent-to-Agent) endpoint**, any A2A-compatible client can discover and call this hosted agent. Copilot CLI can already use MCP tools, so for the demo I expose the Foundry A2A endpoint as a tiny local MCP bridge. Let's prove the chain end to end.

*(stage) **N** opens a second terminal and shows the Copilot A2A bridge command from `src/dem333/copilot_a2a_bridge.py`:*

```bash
cd src
export FOUNDRY_A2A_URL="${AZURE_AI_PROJECT_ENDPOINT}/agents/${HOSTED_AGENT_NAME}/endpoint/protocols/a2a"
export FOUNDRY_A2A_AGENT_CARD_PATH="agentCard/v0.3"

uv run python -m dem333.copilot_a2a_bridge --message "Reply exactly A2A bridge ready."
```

*(stage) Then **N** starts Copilot CLI with that bridge as an MCP server:*

```bash
cat > /tmp/copilot-a2a-bridge.json <<JSON
{
  "mcpServers": {
    "copilot-a2a-bridge": {
      "command": "uv",
      "args": ["--directory", "$PWD", "run", "python", "-m", "dem333.copilot_a2a_bridge"],
      "env": {
        "FOUNDRY_A2A_URL": "$FOUNDRY_A2A_URL",
        "FOUNDRY_A2A_AGENT_CARD_PATH": "agentCard/v0.3"
      }
    }
  }
}
JSON

copilot --additional-mcp-config @/tmp/copilot-a2a-bridge.json --allow-all-tools --allow-all-urls
```

*(stage) Inside Copilot CLI:*

> `Use the ask_dem333_agent tool to ask: what are the top 3 things in my inbox right now?`

*(stage) Copilot CLI calls the MCP bridge, the bridge invokes the Foundry A2A endpoint, the hosted LangGraph agent loads the inbox-triage skill, calls Work IQ Mail, and responds. Output appears inside Copilot CLI.*
**F:** Stop and look at what just happened. **Copilot CLI** — a totally different agent runtime — called an MCP tool that crossed into **A2A**, reached *our* LangGraph agent hosted in Foundry, which then used another MCP tool to read my mailbox, applied a skill, and answered. **None of those pieces had to know about each other.** That's the open-source story end-to-end.
**F:** Stop and look at what just happened. **Copilot CLI** — a totally different agent runtime — called an MCP tool that crossed into **A2A**, reached *our* LangGraph agent hosted in Foundry, which then used another MCP tool to read my mailbox, applied a skill, and answered. **None of those pieces had to know about each other.** That's the open-source story end-to-end.

---

## Wrap-up — ⏱ 1 min

**F:** I think this is enough for today, this code is available so clone it and you can run every step of what we just did.

Thanks Nagkumar for this fantastic demo, thanks everyone. We'll stick around for questions.

*(stage) End slide with QR code → repo URL.*

---

## Timing budget recap

| Section | Time | Cumulative |
|---|---:|---:|
| 1. Intro | 2:00 | 2:00 |
| 2. Objective / OpenClaw framing | 2:00 | 4:00 |
| 3. LangGraph agent loop | 3:00 | 7:00 |
| 4. First console interaction | 1:30 | 8:30 |
| 5. MCP — Work IQ Mail | 4:00 | 12:30 |
| 6. Skills — inbox triage | 4:00 | 16:30 |
| 7. Playwright browser | 4:00 | 20:30 |
| 8. Responses API on Foundry | 3:00 | 23:30 |
| 9. OpenTelemetry | 3:00 | 26:30 |
| 10. A2A from Copilot CLI | 2:30 | 29:00 |
| Wrap-up | 1:00 | 30:00 |

## Pre-flight checklist (run before going on stage)

- [ ] `cd src && uv run python main.py --agent demo` boots clean
- [ ] `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` set; MSAL token cached (no auth popup mid-demo)
- [ ] At least 5 recent emails in the demo mailbox (seed if needed)
- [ ] `@playwright/cli` installed; browser session `dem333` opens without prompting
- [ ] Hosted deployment command from `docs/HOSTED_AGENT_DEPLOYMENT.md` already executed once; redeploy fast path documented
- [ ] Copilot CLI installed, logged in, and `/tmp/copilot-a2a-bridge.json` points at the hosted A2A bridge
- [ ] Terminal font ≥ 16pt, dark theme, line wrap on
