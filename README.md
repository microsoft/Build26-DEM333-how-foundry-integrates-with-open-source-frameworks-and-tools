# 🚀 Get Started

**This repo is where attendees go to continue their learning after your session — and your Copilot agent will help you set it up.**

### Step 1: Open your repo

Open this repo in a **Codespace** (click the green **Code** button → **Create a Codespace**) — or clone it locally. Then open **GitHub Copilot Chat**.

### Step 2: Add your content

Give the agent something to work with. Drag files into the Explorer panel — session abstracts, outlines, screenshots, notes — and drop them in one of two places:

| Where to put it | What goes there | Who sees it |
| --- | --- | --- |
| **`_remove-before-publish/`** | Internal reference materials (abstracts, outlines, screenshots, planning docs) | **Copilot only** — never published |
| **`/docs/`, `/src/`, or repo root** | Lab instructions, demo code, sample data, getting-started guides | **Attendees** — published with the repo |

> 💡 Not sure? Start by dropping your session abstract or outline into `_remove-before-publish/`. The agent will figure out what to do with it.

### Step 3: Ask the Agent

Once your content is in the repo, use these three phrases with Copilot to build out your session repo:

| Phrase to use with Copilot | What it does | When to run it |
| --- | --- | --- |
| **"Help me get started"** | Sets up session title, description, outcomes, and owners | After you've added your session abstract or outline to the repo |
| **"Help me refine content"** | Organizes your session content into the repo | Each time you add or update content |
| **"Help me finalize"** | Final review, cleanup, and publication prep | When you're ready to publish |

> 💡 **These three phrases are just the starting point.** Copilot can do much more — try asking it to brainstorm next steps for attendees, generate code samples, or build out your repo structure. Don't be afraid to put it in plan mode and ask for what you need.

---

<a name="start-building"></a>
<br>
<p align="center">
<img src="img/banner-build-26.png" alt="Microsoft Build 2026" width="1200"/>
</p>

# [Microsoft Build 2026](https://build.microsoft.com)

## 🔥 DEM333: How Foundry integrates with open-source frameworks and tools

### Session Description

In this demo, we'll show how Microsoft Foundry integrates with the open-source tools developers already use so you can build agents your way and deploy them with enterprise-grade hosting and observability built in. We'll start with Microsoft Agent Framework, bring in a LangGraph specialist, connect agents with A2A, expose the experience to user-facing apps with AG-UI, perform safe tool actions through MCP and skills, and inspect the full multi-agent run with OpenTelemetry.

### 🚀 Getting started

The main demo lives in [`src/dem333`](src/dem333/). To explore it locally:

1. Open this repository in a Codespace or clone it locally.
1. Create a Python environment and install dependencies:

   ```bash
   cd src/dem333
   python3 -m venv .venv
   . .venv/bin/activate
   python3 -m pip install -r requirements.txt
   ```

1. Copy the sample environment file and fill in your Azure OpenAI values:

   ```bash
   cp .env.example .env
   ```

1. Run the local multi-agent demo:

   ```bash
   python3 scripts/run_demo.py
   ```

1. Optional: run the AG-UI gateway after the local coordinator is running:

   ```bash
   PYTHONPATH=src python3 scripts/run_agui_gateway.py
   ```

### 🧠 Learning Outcomes

By the end of this session, you will be able to:

- Explain how Foundry can host and observe agents built with open frameworks and protocols.
- Connect a Microsoft Agent Framework coordinator to LangGraph and policy specialists through Responses and A2A.
- Use OpenTelemetry traces to inspect model calls, agent handoffs, MCP tool actions, skills, latency, and failures across a multi-agent workflow.

### 💬 Keep Learning with Copilot

Try these prompts with GitHub Copilot to explore the topics from this session. Open Copilot Chat in Visual Studio Code (`Ctrl+Alt+I` on Windows/Linux, `Cmd+Shift+I` on Mac), paste a prompt, and see what you learn. Try connecting the [Microsoft Learn MCP Server](#-microsoft-learn-mcp-server) for the latest official documentation.

Use these as a starting point — or write your own!

1. Understand the protocol stack:

   ```text
   Explain how AG-UI, A2A, MCP, Responses, and OpenTelemetry fit together in the DEM333 sample under src/dem333.
   ```

1. Trace the coordinator flow:

   ```text
   Walk me through src/dem333/agents/coordinator_agent/main.py and explain how the Microsoft Agent Framework workflow delegates to specialists.
   ```

1. Extend the demo:

   ```text
   Help me add one new MCP action to src/dem333/src/dem333_common/mcp_action_server.py and surface its receipt in the final coordinator response.
   ```

### 💻 Technologies Used

1. [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/) and hosted agents
1. [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/)
1. [LangGraph](https://langchain-ai.github.io/langgraph/)
1. [OpenTelemetry with Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable)
1. [Model Context Protocol](https://modelcontextprotocol.io/)
1. [Agent User Interaction Protocol](https://docs.ag-ui.com/introduction)
1. [Azure OpenAI in Foundry Models](https://learn.microsoft.com/azure/ai-foundry/openai/)

### 📚 Resources and Next Steps

| Resource | Description |
| :--- | :--- |
| [https://aka.ms/build26-next-steps](https://aka.ms/build26-next-steps) | Explore lab and session repos to further your learning from Microsoft Build |
| [DEM333 demo source](src/dem333/) | Source code, local runner, Dockerfiles, Foundry agent metadata, and AG-UI gateway for the session demo |
| [DEM333 talk script](src/dem333/docs/talk-script.md) | Rough speaker script, stage directions, and trace callouts |
| [Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/) | Learn how to build, deploy, evaluate, and observe AI apps and agents in Foundry |
| [Microsoft Agent Framework documentation](https://learn.microsoft.com/agent-framework/) | Learn how to build workflow-based and agent-based applications with Microsoft Agent Framework |
| [Azure Monitor OpenTelemetry documentation](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable) | Configure OpenTelemetry export to Azure Monitor and Application Insights |


### 🌟 Microsoft Learn MCP Server

The Microsoft Learn MCP Server gives your AI agent direct access to Microsoft's official documentation — grounded, up-to-date answers about the products and services covered in this session.

**Visual Studio Code** — One click installation:

[![Install in Visual Studio Code](https://img.shields.io/badge/Visual_Studio_Code-Install_Microsoft_Learn_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=microsoft-learn&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Flearn.microsoft.com%2Fapi%2Fmcp%22%7D)


**GitHub Copilot CLI** — Run this to install the Learn MCP Server as a plugin:
```
/plugin install microsoftdocs/mcp
```

For more info, other clients, and to post questions, visit the [Learn MCP Server repo](https://aka.ms/learnmcp).

## Content Owners

<table>
<tr>
    <td align="center"><a href="https://github.com/nagkumar91">
        <img src="https://github.com/nagkumar91.png" width="100px;" alt="Nagkumar Arkalgud"/><br />
        <sub><b>Nagkumar Arkalgud</b></sub></a><br />
            <a href="https://github.com/nagkumar91" title="GitHub profile">📢</a>
    </td>
</tr></table>

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
