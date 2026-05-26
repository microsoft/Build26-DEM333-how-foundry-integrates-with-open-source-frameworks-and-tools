import asyncio
import logging
from typing import TypedDict

from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponsesAgentServerHost,
    ResponsesServerOptions,
    TextResponse,
)
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from dem333_common.actions import ActionReceipt, format_receipts
from dem333_common.llm import get_chat_model
from dem333_common.mcp_action_client import call_mcp_tool
from dem333_common.telemetry import agent_span, configure_observability
from dem333_common.text import detect_city, detect_days


SERVICE_NAME = "dem333-itinerary-agent"
logger = logging.getLogger(SERVICE_NAME)

load_dotenv(override=False)
configure_observability(SERVICE_NAME)


class PlannerState(TypedDict):
    request: str
    city: str
    days: int
    constraints: str
    schedule: list[str]
    critique: str
    actions: list[ActionReceipt]
    answer: str


async def parse_request(state: PlannerState) -> PlannerState:
    model = get_chat_model(temperature=0.1, max_completion_tokens=350)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are an executive briefing planner. Extract planning constraints, customer goals, "
                    "stakeholders, and known risks from the request. Return concise bullets."
                )
            ),
            HumanMessage(content=state["request"]),
        ],
        config={"metadata": {"langgraph_node": "parse_request", "agent_name": SERVICE_NAME}},
    )
    return {
        **state,
        "city": detect_city(state["request"]),
        "days": detect_days(state["request"]),
        "constraints": str(response.content),
    }


async def draft_schedule(state: PlannerState) -> PlannerState:
    model = get_chat_model(temperature=0.25, max_completion_tokens=420)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You design high-signal customer visit itineraries. Create a concise day-by-day plan with "
                    "executive moments, technical work, owners, and decision checkpoints. Keep it under 240 words."
                )
            ),
            HumanMessage(
                content=(
                    f"City: {state['city']}\nDays: {state['days']}\n"
                    f"Constraints and goals:\n{state['constraints']}\n\n"
                    f"Original request:\n{state['request']}"
                )
            ),
        ],
        config={"metadata": {"langgraph_node": "draft_schedule", "agent_name": SERVICE_NAME}},
    )
    return {**state, "schedule": [str(response.content)]}


async def critique_schedule(state: PlannerState) -> PlannerState:
    model = get_chat_model(temperature=0.1, max_completion_tokens=280)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a skeptical chief of staff. Critique the itinerary for executive clarity, "
                    "risk, missing decision points, and stage-demo readiness. Return at most 6 terse bullets."
                )
            ),
            HumanMessage(
                content=(
                    f"Original request:\n{state['request']}\n\n"
                    f"Draft itinerary:\n{state['schedule'][0]}"
                )
            ),
        ],
        config={"metadata": {"langgraph_node": "critique_schedule", "agent_name": SERVICE_NAME}},
    )
    return {**state, "critique": str(response.content)}


async def perform_actions(state: PlannerState) -> PlannerState:
    room_receipt = await call_mcp_tool(
        SERVICE_NAME,
        "reserve_demo_room",
        {
            "city": state["city"],
            "days": state["days"],
            "audience": "executive customer briefing",
        },
    )
    brief_receipt = await call_mcp_tool(
        SERVICE_NAME,
        "create_executive_brief",
        {
            "city": state["city"],
            "title": f"{state['city']} customer visit run-of-show",
            "owner": "account team",
        },
    )
    return {**state, "actions": [room_receipt, brief_receipt]}


async def format_answer(state: PlannerState) -> PlannerState:
    model = get_chat_model(temperature=0.2, max_completion_tokens=500)
    actions_text = format_receipts(state["actions"], "Actions performed through MCP")
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are the itinerary specialist. Refine the draft using the critique and produce "
                    "a polished answer with sections: Summary, Itinerary, Decision points, Actions, Demo note. "
                    "Keep it under 330 words."
                )
            ),
            HumanMessage(
                content=(
                    f"City: {state['city']} ({state['days']} days)\n"
                    f"Constraints:\n{state['constraints']}\n\n"
                    f"Draft itinerary:\n{state['schedule'][0]}\n\n"
                    f"Critique:\n{state['critique']}\n\n"
                    f"{actions_text}"
                )
            ),
        ],
        config={"metadata": {"langgraph_node": "format_answer", "agent_name": SERVICE_NAME}},
    )
    answer = (
        f"LangGraph itinerary specialist LLM plan for {state['city']} ({state['days']} day(s)):\n"
        f"{response.content}\n\n"
        f"{actions_text}"
    )
    return {**state, "answer": answer}


def build_graph():
    graph = StateGraph(PlannerState)
    graph.add_node(
        "parse_request",
        parse_request,
        metadata={"langgraph_node": "parse_request", "agent_name": SERVICE_NAME},
    )
    graph.add_node(
        "draft_schedule",
        draft_schedule,
        metadata={"langgraph_node": "draft_schedule", "agent_name": SERVICE_NAME},
    )
    graph.add_node(
        "critique_schedule",
        critique_schedule,
        metadata={"langgraph_node": "critique_schedule", "agent_name": SERVICE_NAME},
    )
    graph.add_node(
        "perform_actions",
        perform_actions,
        metadata={"langgraph_node": "perform_actions", "agent_name": SERVICE_NAME},
    )
    graph.add_node(
        "format_answer",
        format_answer,
        metadata={"langgraph_node": "format_answer", "agent_name": SERVICE_NAME},
    )
    graph.add_edge(START, "parse_request")
    graph.add_edge("parse_request", "draft_schedule")
    graph.add_edge("draft_schedule", "critique_schedule")
    graph.add_edge("critique_schedule", "perform_actions")
    graph.add_edge("perform_actions", "format_answer")
    graph.add_edge("format_answer", END)
    return graph.compile(name="dem333-itinerary-langgraph")


GRAPH = build_graph()
app = ResponsesAgentServerHost(
    options=ResponsesServerOptions(default_fetch_history_count=10)
)


async def _single_chunk(text: str):
    yield text


@app.response_handler
async def handle_create(
    request: CreateResponse,
    context: ResponseContext,
    cancellation_signal: asyncio.Event,
):
    user_request = await context.get_input_text() or ""
    if user_request.lower().startswith("health check for "):
        return TextResponse(context, request, text=_single_chunk(f"{SERVICE_NAME} is ready"))

    with agent_span(
        SERVICE_NAME,
        f"invoke_agent {SERVICE_NAME}",
        context_carrier=context.client_headers,
        **{
            "gen_ai.system": "azure.ai.foundry",
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": SERVICE_NAME,
            "dem333.surface": "langgraph",
            "azure.ai.agentserver.response_id": context.response_id,
            "gen_ai.conversation.id": context.conversation_id,
            "dem333.input_length": len(user_request),
        },
    ):
        logger.info("Running LangGraph itinerary planner")
        result = await GRAPH.ainvoke(
            {
                "request": user_request,
                "city": "",
                "days": 0,
                "constraints": "",
                "schedule": [],
                "critique": "",
                "actions": [],
                "answer": "",
            },
            config={
                "metadata": {
                    "agent_name": SERVICE_NAME,
                    "agent_id": SERVICE_NAME,
                    "conversation_id": context.conversation_id or context.response_id,
                }
            },
        )
    return TextResponse(context, request, text=_single_chunk(result["answer"]))


if __name__ == "__main__":
    app.run()
