# DEM333 interactive talk script

## Cast

- **Fauncdo**: audience proxy, keeps asking "can the agent also do this?"
- **Nagkumar**: live builder, makes small changes and shows the result.

## Opening

**Nagkumar:** "Instead of showing a finished black box, we are going to build this demo interactively. Fauncdo will keep pushing the agent with new asks, I will add one capability at a time, and then we will inspect the exact trace so you can see how Foundry hosts and observes the system."

**Fauncdo:** "So this is not just a prompt demo?"

**Nagkumar:** "Right. The goal is to show the open surfaces developers actually use: MCP for tools, Microsoft Agent Framework for workflow, LangGraph for specialist logic, skills for repeatable actions, Responses for hosted agent APIs, A2A for agent-to-agent calls, AG-UI for user-facing streams, and OpenTelemetry for observability."

## Beat 0: Baseline hosted coordinator

**Fauncdo:** "What do we already have running?"

**Nagkumar:** "We start with a coordinator hosted in Foundry. It exposes a Responses endpoint, so I can invoke it like a normal hosted agent."

**Stage direction:** Run the baseline request against the coordinator.

```text
Summarize what you can help with for an executive customer visit.
```

**Nagkumar:** "At this point the agent can plan, but it does not yet know anything about my mailbox. In Foundry, the trace starts with the hosted invocation and the Responses request."

**Trace callout:** Point to the hosted-agent root span and `dem333.surface=responses-protocol`.

## Beat 1: Add Outlook through MCP

**Fauncdo:** "Can I ask the agent to get email?"

**Nagkumar:** "Yes, but I do not want email logic buried in the agent. I will connect Outlook through MCP so mail access is a tool surface with explicit permissions."

**Stage direction:** Apply the small prepared change that registers the Outlook/Microsoft Graph MCP server and updates the coordinator instructions to use the read-only mail summary tool.

**Nagkumar:** "Now I can ask the same hosted agent a richer question."

```text
Look at the latest emails for the Contoso customer visit and summarize what I need to respond to.
```

**Fauncdo:** "The answer came back with email context. How do we know what happened?"

**Nagkumar:** "The trace shows a model call deciding to use a tool, an MCP tool call to Outlook, and a tool result returning only the demo-safe summary we allow."

**Trace callout:** Show `dem333.surface=mcp`, the Outlook tool name, latency, and a sanitized action receipt. Call out that a real production deployment should redact or sample sensitive mail content.

## Beat 2: Turn email into a plan

**Fauncdo:** "Can it turn those emails into an actual visit plan?"

**Nagkumar:** "This is where I do not want one giant prompt. The coordinator uses Microsoft Agent Framework as an explicit workflow: plan the delegation, call specialists, perform actions, and synthesize the response."

**Stage direction:** Route the Outlook summary into the existing coordinator workflow and itinerary specialist.

```text
Use those customer emails to create a two-day executive visit plan with meetings, prep work, and open questions.
```

**Nagkumar:** "The itinerary specialist is built with LangGraph. It has nodes for parsing the request, drafting the schedule, critiquing it, taking safe prep actions, and formatting the answer."

**Fauncdo:** "So LangGraph is still LangGraph, but Foundry can host and observe it?"

**Nagkumar:** "Exactly. Foundry is not forcing every agent into one framework. The specialist can stay a LangGraph app while the coordinator calls it as a hosted agent."

**Trace callout:** Show `dem333.surface=maf` for workflow steps and `dem333.surface=langgraph` for itinerary nodes.

## Beat 3: Add policy and readiness checks

**Fauncdo:** "Can it tell us what is risky before we reply to the customer?"

**Nagkumar:** "I will add the policy specialist as another hosted agent and call it over A2A. The coordinator does not import that agent's code; it sends an A2A `message/send` request."

**Stage direction:** Enable or show the A2A endpoint for the policy specialist and configure the coordinator with the specialist URL.

```text
Before I send this plan, check policy, privacy, accessibility, procurement, and commitment risks.
```

**Nagkumar:** "The response now includes a policy section and readiness receipts. Those receipts come from skills, which are useful for repeatable procedures that should be easy to name, trace, and govern."

**Fauncdo:** "So A2A is the agent-to-agent part, and skills are the repeatable procedure part?"

**Nagkumar:** "Yes. A2A connects independent agents. Skills package repeatable work inside an agent. MCP connects agents to external tools like Outlook."

**Trace callout:** Show `dem333.surface=a2a`, `a2a.message_send`, and `dem333.surface=skill`.

## Beat 4: Show the user-facing stream with AG-UI

**Fauncdo:** "This is useful in a terminal, but can a frontend show what the agent is doing?"

**Nagkumar:** "That is where AG-UI fits. It is the user-facing event stream. The frontend does not need to know whether the backend uses MAF, LangGraph, A2A, or MCP. It sees standard run, state, tool-call, text, and error events."

**Stage direction:** Send the same request through the AG-UI gateway.

**Nagkumar:** "Watch the stream: `RUN_STARTED`, `STATE_SNAPSHOT`, a tool call to the coordinator, streamed text, and `RUN_FINISHED`."

**Fauncdo:** "So AG-UI is not replacing A2A?"

**Nagkumar:** "Right. AG-UI connects the user experience to the agent system. A2A connects agents to other agents. MCP connects agents to tools. OpenTelemetry ties all of it together."

**Trace callout:** Show `dem333.surface=ag-ui` followed by the nested coordinator call.

## Beat 5: Copilot CLI as an external agent making an A2A call

**Fauncdo:** "What if the caller is not our app? Can another agent call this agent?"

**Nagkumar:** "I will spin up Copilot CLI as the caller. For the demo, Copilot CLI is registered as an external agent using the Foundry external-agent observability sample, and its SDK traces export to the same Application Insights resource."

**Stage direction:** Start the Copilot CLI flow and ask it to call the DEM333 coordinator over A2A.

```text
Call the DEM333 coordinator over A2A. Ask it to summarize the latest Contoso visit emails, produce a compliant visit plan, and return the policy risks.
```

**Nagkumar:** "Now Copilot CLI is not just a terminal helper. In the trace it appears as an external agent that calls the Foundry-hosted coordinator through A2A."

**Fauncdo:** "And the same trace still includes Outlook, the specialists, and the final response?"

**Nagkumar:** "Yes. This is the payoff: an external agent, an A2A handoff, hosted Foundry agents, MCP Outlook access, LangGraph specialist work, skills, and model calls all show up in the same observability story."

**Trace callout:** Open Foundry/App Insights and follow the span chain: `external-agent` -> `a2a` -> hosted coordinator -> MAF workflow -> Outlook MCP -> policy specialist -> itinerary specialist -> LangGraph nodes -> skill receipts -> final response.

## Closing

**Nagkumar:** "The takeaway is that Foundry lets us bring open frameworks and protocols into an enterprise agent platform. We did not rewrite the app each time Fauncdo asked for a new capability. We added one interoperable surface at a time."

**Fauncdo:** "And the audience can see not only that it worked, but how it worked."

**Nagkumar:** "Exactly. The demo is not magic. It is a hosted, observable system: MCP for tools, MAF and LangGraph for agent logic, skills for repeatable procedures, Responses and A2A for agent APIs, AG-UI for the user experience, and OpenTelemetry so Foundry can help us debug, govern, and operate it."

## Fallback script

If live Outlook auth or tenant access fails, use a seeded email fixture and say: "The tool result is replayed from the same schema the Outlook MCP tool returns." If Copilot CLI tracing fails, show a captured trace from the same Application Insights resource and continue the story from the external-agent root span. The core message remains the same: each capability is connected through an open surface and observed through the same trace pipeline.
