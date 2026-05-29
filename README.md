<a name="start-building"></a>
<br>
<p align="center">
<img src="img/banner-build-26.png" alt="Microsoft Build 2026" width="1200"/>
</p>

# [Microsoft Build 2026](https://build.microsoft.com)

## 🔥 DEM333: How Foundry Integrates With Open Source Frameworks and Tools

### Session Description

This demo walks through building a practical OpenClaw like agent using open-source technologies and then operationalizing the same solution in Microsoft Foundry. You will see how to connect enterprise tools with the Model Context Protocol, codify repeatable behavior with skills, add browser automation with Playwright CLI, observe with OpenTelemetry, and move from local development to cloud-hosted agents using open protocols like Responses API and A2A to agent-to-agent communication.

### 🚀 Getting started

If you're following this demo at your own pace:
- Clone this repository
- Follow the setup instructions in [docs/PREREQ.md](docs/PREREQ.md)
- Configure environment variables in `.env` file.
- Run the local agent with `cd src && uv run main.py`
- Deploy the same agent as a Foundry hosted agent with [docs/HOSTED_AGENT_DEPLOYMENT.md](docs/HOSTED_AGENT_DEPLOYMENT.md)
- Review the walkthrough in [docs/SCRIPT.md](docs/SCRIPT.md)

### 🧠 Learning Outcomes

By the end of this demo, you will be able to:

- Build a LangGraph-based agent loop and connect it to external enterprise actions by using the Model Context Protocol.
- Improve agent quality by combining reusable skills with focused tool surfaces such as Work IQ mail tools and Playwright CLI browser actions.
- Expose an open-source agent implementation through Microsoft Foundry endpoints and understand how to add tracing and cross-agent interoperability.

### 💬 Keep Learning with Copilot

Try these prompts with GitHub Copilot to explore the topics from this demo. Open Copilot Chat in Visual Studio Code (`Ctrl+Alt+I` on Windows/Linux, `Cmd+Shift+I` on Mac), paste a prompt, and see what you learn. Try connecting the [Microsoft Learn MCP Server](#-microsoft-learn-mcp-server) for the latest official documentation.

1. Understand the architecture and building blocks:

```text
Explain the architecture in this DEM333 repo, including how LangGraph, skills, MCP tools, and Microsoft Foundry fit together. Then suggest one beginner-friendly extension to implement first.
```

2. Ground setup guidance with official documentation:

```text
Using the Microsoft Learn MCP Server, find the latest Microsoft Foundry and Model Context Protocol docs needed for this repo, then produce a concise setup checklist for local development and deployment.
```

3. Build an advanced extension:

```text
Help me add a new skill that summarizes inbox triage results into a daily digest, and update the agent flow so it can call that skill after classification. Include tests and a short validation plan.
```

### 💻 Technologies Used

1. [Microsoft Foundry Models](https://learn.microsoft.com/azure/foundry/concepts/foundry-models-overview)
1. [Azure OpenAI in Microsoft Foundry Models v1 API](https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle)
1. [Model Context Protocol tooling in Microsoft Foundry Agents](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol)
1. [Tracing and observability in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup)
1. [Microsoft Entra ID app registration quickstart](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)

### 📚 Resources and Next Steps

| Resource | Description |
|:---------|:------------|
| [https://aka.ms/build26-next-steps](https://aka.ms/build26-next-steps) | Explore lab and session repos to further your learning from Microsoft Build |


### 🌟 Microsoft Learn MCP Server

The Microsoft Learn MCP Server gives your AI agent direct access to Microsoft's official documentation — grounded, up-to-date answers about the products and services covered in this demo.

**Visual Studio Code** — One click installation: 

[![Install in Visual Studio Code](https://img.shields.io/badge/VS_Code-Install_Microsoft_Learn_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=microsoft-learn&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Flearn.microsoft.com%2Fapi%2Fmcp%22%7D)


**GitHub Copilot CLI** — Run this to install the Learn MCP Server as a plugin:
```
/plugin install microsoftdocs/mcp
```

For more info, other clients, and to post questions, visit the [Learn MCP Server repo](https://aka.ms/learnmcp).

## Content Owners

<table>
<tr>
    <td align="center"><a href="https://github.com/santiagxf">
        <img src="https://avatars.githubusercontent.com/u/32112894?v=4" width="100px;" alt="Facundo Santiago"/><br />
        <sub><b>Facundo Santiago</b></sub></a><br />
            <a href="https://github.com/santiagxf" title="talk">📢</a>
    </td>
    <td align="center"><a href="https://github.com/nagkumar91">
        <img src="https://github.com/nagkumar91.png?size=100" width="100px;" alt="nagkumar91"/><br />
        <sub><b>nagkumar91</b></sub></a><br />
            <a href="https://github.com/nagkumar91" title="code">💻</a>
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
