# DEM333 interactive demo plan

## Thesis

DEM333 becomes an interactive "build the agent in front of the audience" demo. Fauncdo asks whether the agent can do something useful, Nagkumar makes a small targeted change, the hosted agent responds, and the audience immediately sees the handoff or tool call in Foundry/App Insights traces. The through line is that Foundry hosts and observes the system while open frameworks and protocols keep each layer swappable.

## Live arc

| Beat | Fauncdo asks | Nagkumar changes live | What the audience sees | Main surface |
| --- | --- | --- | --- | --- |
| 0. Baseline hosted agent | "What do we already have running?" | Start with the DEM333 coordinator hosted in Foundry behind the Responses endpoint. | A basic customer-visit planning response and a top-level hosted-agent trace. | Foundry hosted agents, Responses, OTel |
| 1. Outlook email | "Can I ask the agent to get email?" | Connect an Outlook/Microsoft Graph MCP server to a demo mailbox and add a read-only mail summary tool to the coordinator's tool list/instructions. | The agent summarizes recent customer email and cites an MCP action receipt. | MCP, skills, OTel |
| 2. Better planning | "Can it turn those emails into a visit plan?" | Route the request into the existing Microsoft Agent Framework coordinator workflow and LangGraph itinerary specialist. | The itinerary specialist turns email context into agenda options, constraints, and next steps. | MAF, LangGraph, hosted specialists |
| 3. Policy check | "Can it tell us what is risky before we reply?" | Add the policy specialist as a hosted A2A target and keep policy/readiness checks as skills. | The response includes compliance, privacy, accessibility, and commitment guardrails. | A2A, skills, Responses |
| 4. User-facing stream | "Can a frontend show what the agent is doing?" | Put the AG-UI gateway in front of the coordinator. | `RUN_STARTED`, state, tool-call, text, and finish events stream to the terminal or UI. | AG-UI |
| 5. External agent caller | "Can another agent call this one?" | Start Copilot CLI as an external agent, instrument it with the Foundry external-agent observability sample, and have it make an A2A call to the coordinator. | Foundry shows the external Copilot CLI span, the A2A call, the hosted coordinator, specialist calls, MCP Outlook access, and model/tool spans in one trace. | External agents, A2A, OTel |

## Demo assets to prepare

- A demo mailbox with seeded customer emails that are safe to show.
- An Outlook/Microsoft Graph MCP server configured for the demo tenant and limited to the least-privilege read scopes needed for the mail summary beat.
- A small pre-staged code/config patch for each live change so the demo can move quickly without typing long blocks on stage.
- A Copilot CLI external-agent launcher based on the [Foundry external agents observability sample](https://github.com/microsoft-foundry/foundry-samples/tree/main/samples/python/external-agents/observability) that exports OpenTelemetry to the same Application Insights resource as the Foundry hosted agents.
- A fallback transcript or recorded trace for the Outlook and external-agent beats in case live tenant auth or network access fails.

## Observability story

Use one Application Insights resource as the shared trace destination. The trace should let the audience follow this chain:

```text
Copilot CLI external agent
  -> A2A message/send
    -> DEM333 coordinator hosted agent
      -> Responses request handling
      -> Microsoft Agent Framework workflow
      -> Outlook MCP tool call
      -> policy specialist over A2A
      -> itinerary specialist over A2A
      -> LangGraph itinerary nodes
      -> skill action receipts
      -> final response
```

Expected attributes and labels:

- `dem333.surface=external-agent` for Copilot CLI spans.
- `dem333.surface=a2a` for agent-to-agent calls.
- `dem333.surface=responses-protocol` for hosted Responses endpoints.
- `dem333.surface=maf` for coordinator workflow stages.
- `dem333.surface=langgraph` for itinerary graph nodes.
- `dem333.surface=mcp` for Outlook and demo action tools.
- `dem333.surface=skill` for policy/readiness skills.
- GenAI semantic attributes for model invocation metadata, with email content sanitized or limited to demo-safe examples.

## Safety and privacy guardrails

- Use a dedicated demo mailbox, not a personal inbox.
- Start with read-only mail access; only add write actions if they are scoped to draft creation in the demo mailbox.
- Do not store secrets in the repo. Use managed identity, federated credentials, or local user auth for the live demo.
- Be deliberate about trace content. If showing email snippets, use seeded demo data and call out why production systems should redact or sample sensitive content.

## Audience takeaway

"We did not rebuild everything every time the requirement changed. We added one open surface at a time: MCP for Outlook tools, MAF and LangGraph for orchestration, A2A for hosted-agent collaboration, AG-UI for the user experience, and OpenTelemetry so both hosted and external agents show up in Foundry."
