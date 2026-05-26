# DEM333 rough talk script

## 0. Setup line

"In this demo, I want to show how we can take agents built with open Python frameworks and protocols, bring them into Foundry, connect them to a user-facing application with AG-UI, connect them to each other through agent-to-agent handoffs, and still operate the whole system with trace-level observability."

## 1. Problem framing

"Most teams do not have one monolithic agent. They have a mix: one team may build a LangGraph agent, another may expose a hosted Responses agent, another may package repeatable work as skills or MCP tools, and the product team still needs a user-facing app. The hard part is not just building an agent; it is connecting users, agents, tools, and observability without custom glue everywhere."

## 2. Introduce the scenario

"Our sample is an executive customer-visit planner. The user asks for a compliant two-day Seattle visit for a healthcare customer. That sounds simple, but it actually needs several kinds of work: itinerary planning, policy review, briefing prep actions, and a final executive-ready synthesis."

Suggested prompt:

```text
Plan a 2-day customer visit to Seattle for a healthcare customer. Make it executive-friendly, keep it compliant, and go ahead with the safe prep actions needed for the briefing.
```

## 3. Show AG-UI as the user-facing layer

"Before we even get to agent-to-agent, we need a way for a user-facing app to talk to this system. That is where AG-UI fits. It is an event protocol for streaming runs, messages, tool calls, state, and errors to a frontend."

What to point at:

- `src/dem333_common/agui_gateway.py`
- endpoint `POST /agui`
- the AG-UI stream in the terminal or frontend: `RUN_STARTED`, `STATE_SNAPSHOT`, `STEP_STARTED`, `TOOL_CALL_*`, `TEXT_MESSAGE_*`, `RUN_FINISHED`
- the nested coordinator call that AG-UI surfaces as `dem333_coordinator_responses`

Stage line:

"So the protocol stack is layered: AG-UI connects user to agent, Responses gives us a hosted agent API, A2A connects agent to agent, MCP connects agent to tools, and OpenTelemetry lets us inspect the whole thing."

Optional live line:

"If I open an AG-UI client, it does not need to understand our internal MAF or LangGraph code. It sees a standard event stream: run started, state snapshot, tool call to the coordinator, streamed final text, and run finished."

## 4. Show the coordinator

"The coordinator is the front door. It is exposed through the Responses protocol, but internally it uses Microsoft Agent Framework as a workflow. The workflow has explicit stages: plan the delegation, call the specialists, perform actions, and synthesize the result."

What to point at:

- `agents/coordinator_agent/main.py`
- `build_maf_coordinator()`
- MAF executors: `DelegationPlannerExecutor`, `SpecialistCallExecutor`, `ActionExecutor`, `SynthesisExecutor`

Stage line:

"This is intentionally not hidden in a prompt. The workflow structure is explicit, inspectable, and traceable."

## 5. Show A2A delegation

"When hosted in Foundry, the coordinator can call the specialists over A2A. The specialists remain independent hosted agents, but now they are callable by another agent through a standard JSON-RPC `message/send` flow."

What to point at:

- `src/dem333_common/a2a_client.py`
- span name `a2a.message_send <agent>`
- `DEM333_COORDINATOR_TRANSPORT=a2a`
- `POLICY_AGENT_A2A_URL`
- `ITINERARY_AGENT_A2A_URL`

Stage line:

"This is the key interoperability moment: the coordinator is not importing specialist code. It is invoking other agents."

## 6. Show the LangGraph specialist

"The itinerary specialist is built with LangGraph. It breaks the request into multiple graph nodes: parse the request, draft a schedule, critique it, perform prep actions, and format the answer."

What to point at:

- `agents/itinerary_agent/main.py`
- `build_graph()`
- nodes: `parse_request`, `draft_schedule`, `critique_schedule`, `perform_actions`, `format_answer`

Stage line:

"This gives us a richer trace than one model call. We can see the reasoning workflow, not just the final answer."

## 7. Show skills and MCP actions

"The demo also shows two ways agents can perform work. Policy and readiness procedures are packaged as skills. Operational actions, like reserving a synthetic briefing room or creating a briefing artifact, are exposed through an MCP stdio server."

What to point at:

- Skills: `src/dem333_common/skills.py`
- MCP server: `src/dem333_common/mcp_action_server.py`
- MCP client: `src/dem333_common/mcp_action_client.py`
- action receipts in the final answer

Stage line:

"These actions are demo-safe. They do not book real rooms or create real tickets; they return deterministic receipts so the audience can match the final answer to the trace."

## 8. Show observability

"Now the most important part: we can open the trace and see the full run. Foundry gives us the hosted invocation, and our OpenTelemetry spans show the coordinator workflow, A2A handoffs, specialist work, LangGraph nodes, MCP tool calls, skills, and nested model calls."

Trace checklist:

- `dem333.surface=responses-protocol`
- `dem333.surface=ag-ui`
- `dem333.surface=maf`
- `dem333.surface=a2a`
- `dem333.surface=langgraph`
- `dem333.surface=mcp`
- `dem333.surface=skill`
- `gen_ai.input.messages`
- `gen_ai.output.messages`
- `gen_ai.operation.name=invoke_agent`
- `gen_ai.operation.name=execute_tool`

Stage line:

"This is what turns a multi-agent demo from magic into an operable system. I can see who called whom, what each model saw, what tools ran, how long each step took, and where I would debug if something failed."

## 9. Close

"The takeaway is that Foundry does not require every agent to be written the same way. You can bring agents built with open frameworks and protocols, expose them to apps with AG-UI and Responses, connect them with A2A, give them tools with MCP, and use OpenTelemetry to understand and govern the end-to-end behavior."

## Short fallback script

"If anything fails live, the story still holds: the local runner shows the same architecture with Responses calls instead of hosted A2A, console spans instead of App Insights, and deterministic MCP/skill receipts instead of real external side effects. The core pattern is the same: build agents with open frameworks, connect them through standard protocols, and observe every step."
