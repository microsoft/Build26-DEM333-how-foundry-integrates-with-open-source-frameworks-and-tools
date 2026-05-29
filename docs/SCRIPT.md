# DEM333 — Demo Script

**Session:** How Foundry Integrates With Open Source Frameworks and Tools
**Speakers:** **Facundo** (narrator / asks the questions) · **Nagkumar** (drives VS Code, shares screen)
**Duration target:** 30 minutes
**Demo project:** `src/` — a "homegrown OpenClaw" built with LangGraph + deepagents + Foundry

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

**F:** Here's the framing. You've all seen *OpenClaw* — a general-purpose agent that can browse the web, read your email, remember you, and run somewhere in the cloud you can call from anywhere. Today, we are going to **build our own OpenClaw, live**, using open-source frameworks and tools — and then we are going to show how **Microsoft Foundry takes that exact same code and supercharges it**.

---

## 3. A minimal agent loop in LangGraph — ⏱ 3 min

**F:** Nagku, let's start at the bottom. If I want to build an agent today — no Foundry, no magic — what's the smallest amount of code I need?

*(stage) **N** opens [src/dem333/agent.py](src/dem333/agent.py) in VS Code.*

**N:** To create a minimal agent you need 2 things: a model and a continuous loop. So let's see an example using LangChain. For the model, we use `init_chat_model` to grab any model — here it's pointing to a GPT model. For the loop, `create_agent` method from langchain gives us a basic agent loop that will wait for my inputs and generate an output.

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

**N:** The `init_chat_model` method automatically reads my environment variables and find the model from a Microsoft Foundry project I have setup. Most Foundry Models implement OpenAI Responses API so I can easily switch to another model if I need to, for example, a DeepSeek model. 

**F:** And what runs that loop?

---

## 4. First interaction in the console — ⏱ 1.5 min

*(stage) **N** opens the integrated terminal. Venv already active.*

**N:** I built a console terminal to execute the loop. Let's just run it.

```bash
python src/main.py
```

*(stage) The DEM333 banner shows up. **N** types:*

> `Hello!`

*(stage) Agent replies with a generic "I'm a helpful assistant…" message.*

**F:** Cool — so we have a working loop. Now, one of the reasons OpenClaw is so popular is because it can do things for you, can it?

**N:** No much. If I ask it to read my email, it'll just apologize. Let's give it a hand.

---

## 5. Tools via MCP — connecting Work IQ — ⏱ 4 min

**N:** The open-source pattern for that connecting the agent to an **MCP Server — Model Context Protocol**. In one sentence: MCP is an open standard that lets an agent discover and call tools to perform actions. 

And one of the most powerful MCP servers out there today is **Work IQ** — a first-party server from Microsoft that gives an agent access to **everything in Microsoft 365**: email, calendar, contacts, files, Teams messages, the lot. So let's give this agent access to my email.

*(stage) **N** opens [src/dem333/tools/work_iq.py](src/dem333/tools/work_iq.py).*

**N:** From the agent's point of view, Work IQ is just an MCP endpoint we point at. The mail surface exposes tools like `searchMessages`, `getMessage`, `createMessage`, `sendDraft`, and so on.

**N:** And in [agent.py](src/dem333/agent.py) we wire it in with the open-source `langchain-mcp-adapters` package — **no Foundry SDK required**:

```python
def get_mcp_client() -> MultiServerMCPClient:
    connections = {"mail": build_work_iq_mail_connection()}
    return MultiServerMCPClient(connections)
```

**F:** So you're saying I can take *any* LangGraph agent I already have, and just plug this server over the open protocol?

**N:** That's the whole point. Let me show it live.

*(stage) **N** restarts `python src/main.py` (mail tools now loaded). Prompt:*

> `What's the latest in my mailbox?`

*(stage) The Rich spinner shows the agent calling `mcp_MailTools_graph_mail_searchMessages`. Output is a clean list of 5 messages.*

**F:** Beautiful. So the agent now has hands — but it doesn't yet know *how* to use them well. For example, if I want to triage my inbox, that format is not that useful.

---

## 6. Skills — teaching the agent *how* to use tools — ⏱ 4 min

**N:** Exactly, and that's where **Skills** come into play. A tool is a *verb* — "search messages." A skill is a *playbook* — "here's how you triage an inbox: pull minimal fields first, classify into five categories, score P0–P3, draft replies using these templates, and never fabricate facts." It's a markdown file the agent reads **only when it's relevant**.

*(stage) **N** opens [src/dem333/skills/inbox-triage/SKILL.md](src/dem333/skills/inbox-triage/SKILL.md).*

Skills is an **open format created by Anthropic** — you just write a skill as a **markdown file** with a small frontmatter block. No SDK, no special runtime, no proprietary schema. Any agent that knows the format can load it.

Let's try to run the agent now with skills:

*(stage) Back to the running agent. Prompt:*

> `Triage my inbox.`

*(stage) Watch the spinner: skill loads (`skill: Inbox Triage`), then tool calls fire. The agent prints "WELCOME TO THE TRIAGE SKILL" (the canary from Step 0), pulls minimal fields, classifies, prioritizes, and produces the Priority Queue / Category Summary / Drafts Ready output.*

**F:** While this runs, how is the agent finding these skills we wrote?

**N:** We give the agent **access to the file system** so it can read the skills we wrote. We mount our `dem333/skills` folder under `/skills/`, and the agent can list and read those markdown files on demand.

*(stage) Show the filesystem wiring in [agent.py](src/dem333/agent.py):*

```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={"/skills/": FilesystemBackend(root_dir="dem333/skills", virtual_mode=True)},
)
```

**N:** Now, we see the agent came back with the triage of the inbox.

**F:** Interesting, because we are using the same model, same tools — totally different behavior, because we taught it the *procedure*.

---

## 7. Sophisticated tools — Playwright browser — ⏱ 4 min

**F:** OK — inbox is covered. The other thing OpenClaw is famous for is **browsing the web**. Nagku, what's our open-source story there?

*(stage) **N** opens [src/dem333/tools/browser.py](src/dem333/tools/browser.py) briefly, then [src/dem333/skills/web-browsing/SKILL.md](src/dem333/skills/web-browsing/SKILL.md).*

**N:** We could use an MCP server. However, a more popular approch these days is to use the command line. Microsoft just shipped **`@playwright/cli`** — a command-line wrapper around Playwright designed for agents. Instead of giving the model 40 fine-grained MCP tools (one per browser action), we give it **one tool**: `playwright_cli`, and a **skill** that teaches it the command vocabulary. Same pattern as before — the verbs live in markdown, not in the tool schema. That saves a huge amount of context.

**F:** Let's see it. Ask it the classic shopping question.

*(stage) Prompt in the agent:*

> `Open amazon.com and tell me the price of the first Microsoft-branded coffee cup you find.`

*(stage) Spinner shows `skill: Web Browsing` loaded, then a sequence of `playwright_cli` calls: `open https://amazon.com`, `snapshot`, `type "microsoft coffee cup"`, `press Enter`, `snapshot`, `click e<n>`, `snapshot`. Final answer cites the URL and the price.*

**F:** Three things to call out: the agent picked the *skill* on its own based on the prompt, it used a *single* tool with a free-form `args` string, and the persistent browser session means the next prompt can keep going from where we left off.

---

## 8. From console to cloud — Responses API on Foundry — ⏱ 3 min

**F:** OK Nagku, fair question from the audience: this is all running in a terminal on your laptop. What happens when I want to ship it? I don't want my customers SSH-ing into your machine.

**N:** This is the part where Foundry pays for itself. Foundry hosts agents behind the **OpenAI Responses API** — same protocol millions of developers already know. We don't rewrite the agent — we wrap it.

*(stage) **N** opens a small `server.py` that takes the same `build_agent(...)` function and exposes it as a Responses-compatible endpoint, then runs:*

**N:** Now anything that speaks the Responses API — the OpenAI SDK, curl, a Next.js app — can call our LangGraph agent. I can run it locally, or I can deploy it to the Foundry using azd

*(stage) Show terminal to deploy it

```bash
azd ....
```

I have this agent already deployed so let's take a look.

*(stage) Response streams back.*

**F:** And critically — we did not have to learn a new agent framework to do that. Our agent stayed LangGraph.

---

## 9. OpenTelemetry

**F:** One more thing... because our agent became a bit sophisticated right. How can we see what this agent is doing in details?

**N:** Foundry implements OpenTelemetry using Semantic Conventions for GenAI, which is the same stack used across multiple agentic stacks including GitHub Copipot.

Let's take a look and see one of those traces.

*(stage) show the traces.

## 10. A2A — calling our agent from Copilot CLI — ⏱ 2.5 min

**F:** That's fantastic. But I got one more for you. Because I heard that 2026 is all about agents calling other agents. Is that a thing?

**N:** Yes — Foundry exposes every hosted agent over the **A2A (Agent-to-Agent) protocol** automatically that allow agents to call other agents to create tasks. No extra config. That means any A2A-compatible client can discover and call it. Let's prove it with **GitHub Copilot CLI**.

*(stage) **N** opens a second terminal and registers our Foundry agent as an A2A peer in Copilot CLI:*

```bash
copilot agent add --a2a $FOUNDRY_A2A_URL
```

*(stage) Then, inside Copilot CLI:*

> `@dem333 what are the top 3 things in my inbox right now?`

*(stage) Copilot CLI routes the request over A2A to our Foundry-hosted agent, which loads the inbox-triage skill, calls Work IQ Mail, and responds. Output appears inside Copilot CLI.*

**F:** Stop and look at what just happened. **Copilot CLI** — a totally different agent runtime — called *our* LangGraph agent hosted in Foundry, which then used an MCP tool to read my mailbox, applied a skill, and answered. **None of those pieces had to know about each other.** That's the open-source story end-to-end.

---

## Wrap-up — ⏱ 1 min

**F:** I think this is enought for today, this code is available so clone it and you can run every step of what we just did.

**N:** Thanks everyone. We'll stick around for questions.

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
| 8. Otel | 3:00 | 23:30 |
| 9. Responses API on Foundry | 3:00 | 26:30 |
| 10. A2A from Copilot CLI | 2:30 | 29:00 |
| Wrap-up | 1:00 | 30:00 |

## Pre-flight checklist (run before going on stage)

- [ ] `src/.venv` active, `python src/main.py` boots clean
- [ ] `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` set; MSAL token cached (no auth popup mid-demo)
- [ ] At least 5 recent emails in the demo mailbox (seed if needed)
- [ ] `@playwright/cli` installed; browser session `dem333` opens without prompting
- [ ] `foundry deploy` already executed once; redeploy fast path documented
- [ ] Copilot CLI installed, logged in, A2A peer registered
- [ ] Terminal font ≥ 16pt, dark theme, line wrap on
