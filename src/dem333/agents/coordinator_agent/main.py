import asyncio
import logging
import os
from dataclasses import dataclass, field

from agent_framework import Executor, Message, WorkflowBuilder, WorkflowContext, handler
from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponsesAgentServerHost,
    ResponsesServerOptions,
    TextResponse,
)
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import Never

from dem333_common.a2a_client import A2ACallError, ask_a2a_agent
from dem333_common.actions import ActionReceipt, format_receipts
from dem333_common.llm import get_chat_model
from dem333_common.mcp_action_client import call_mcp_tool
from dem333_common.responses_client import SpecialistCallError, ask_responses_agent
from dem333_common.skills import run_executive_summary_skill
from dem333_common.telemetry import agent_span, configure_observability


SERVICE_NAME = "dem333-coordinator-agent"
logger = logging.getLogger(SERVICE_NAME)

load_dotenv(override=False)
configure_observability(SERVICE_NAME)
logging.getLogger("agent_framework._workflows._runner").setLevel(logging.WARNING)
logging.getLogger("agent_framework._workflows._validation").setLevel(logging.WARNING)

app = ResponsesAgentServerHost(
    options=ResponsesServerOptions(default_fetch_history_count=10)
)


@dataclass
class DelegationPlan:
    user_request: str
    plan: str


@dataclass
class SpecialistOutputs:
    user_request: str
    plan: str
    itinerary: str
    policy: str
    transport: str


@dataclass
class ActionOutputs:
    user_request: str
    plan: str
    itinerary: str
    policy: str
    transport: str
    receipts: list[ActionReceipt] = field(default_factory=list)


def _required_endpoint(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for the coordinator local demo")
    return value


def _optional_endpoint(name: str) -> str | None:
    return os.getenv(name)


async def plan_delegation(user_request: str) -> str:
    model = get_chat_model(temperature=0.1, max_completion_tokens=350)
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are the DEM333 coordinator. Decide how to delegate a customer-visit planning request. "
                    "For this demo, always use both subagents: itinerary and policy. Explain why each is needed "
                    "and what question to ask it."
                )
            ),
            HumanMessage(content=user_request),
        ],
        config={"metadata": {"agent_name": "coordinator-delegation-planner", "dem333.step": "delegation-plan"}},
    )
    return str(response.content)


async def synthesize_answer(
    user_request: str,
    delegation_plan: str,
    itinerary: str,
    policy: str,
    transport: str,
    action_receipts: list[ActionReceipt],
) -> str:
    model = get_chat_model(temperature=0.2, max_completion_tokens=550)
    actions_text = format_receipts(action_receipts, "Coordinator actions performed")
    response = await model.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are the final coordinator for a multi-agent DEM333 demo. Synthesize specialist outputs into "
                    "an executive-ready recommendation in under 350 words. Mention the transport used for subagent "
                    "delegation and call out what to inspect in the trace."
                )
            ),
            HumanMessage(
                content=(
                    f"User request:\n{user_request}\n\n"
                    f"Delegation plan:\n{delegation_plan}\n\n"
                    f"Itinerary specialist output:\n{itinerary}\n\n"
                    f"Policy specialist output:\n{policy}\n\n"
                    f"Subagent transport: {transport}\n\n"
                    f"{actions_text}"
                )
            ),
        ],
        config={"metadata": {"agent_name": "coordinator-final-synthesis", "dem333.step": "final-synthesis"}},
    )
    return (
        "Coordinator response:\n"
        f"Subagent transport: {transport}\n\n"
        f"{response.content}\n\n"
        f"{actions_text}"
    )


async def call_specialists(user_request: str, delegation_plan: str) -> tuple[str, str, str]:
    transport = os.getenv("DEM333_COORDINATOR_TRANSPORT", "a2a").lower()
    if transport == "a2a":
        policy_a2a = _optional_endpoint("POLICY_AGENT_A2A_URL")
        itinerary_a2a = _optional_endpoint("ITINERARY_AGENT_A2A_URL")
        if policy_a2a and itinerary_a2a:
            itinerary_result, policy_result = await asyncio.gather(
                ask_a2a_agent(
                    itinerary_a2a,
                    (
                        "Use the delegation plan and build the itinerary.\n\n"
                        f"Delegation plan:\n{delegation_plan}\n\nUser request:\n{user_request}"
                    ),
                    target_agent_name="dem333-itinerary-agent",
                ),
                ask_a2a_agent(
                    policy_a2a,
                    (
                        "Use the delegation plan and review policy/compliance guardrails.\n\n"
                        f"Delegation plan:\n{delegation_plan}\n\nUser request:\n{user_request}"
                    ),
                    target_agent_name="dem333-policy-agent",
                ),
            )
            return itinerary_result.text, policy_result.text, "a2a"
        if not os.getenv("DEM333_ALLOW_RESPONSES_FALLBACK"):
            missing = [
                name
                for name, value in {
                    "POLICY_AGENT_A2A_URL": policy_a2a,
                    "ITINERARY_AGENT_A2A_URL": itinerary_a2a,
                }.items()
                if not value
            ]
            raise A2ACallError("a2a", f"missing A2A endpoint(s): {', '.join(missing)}")

    policy_endpoint = _required_endpoint("POLICY_AGENT_RESPONSES_URL")
    itinerary_endpoint = _required_endpoint("ITINERARY_AGENT_RESPONSES_URL")
    itinerary_result, policy_result = await asyncio.gather(
        ask_responses_agent(
            itinerary_endpoint,
            (
                "Use the delegation plan and build the itinerary.\n\n"
                f"Delegation plan:\n{delegation_plan}\n\nUser request:\n{user_request}"
            ),
            target_agent_name="dem333-itinerary-agent",
        ),
        ask_responses_agent(
            policy_endpoint,
            (
                "Use the delegation plan and review policy/compliance guardrails.\n\n"
                f"Delegation plan:\n{delegation_plan}\n\nUser request:\n{user_request}"
            ),
            target_agent_name="dem333-policy-agent",
        ),
    )
    return itinerary_result.text, policy_result.text, "responses-fallback" if transport == "a2a" else "responses"


async def _single_chunk(text: str):
    yield text


def _latest_message_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        text = (getattr(message, "text", "") or "").strip()
        if text:
            return text
    return ""


class DelegationPlannerExecutor(Executor):
    @handler
    async def plan(self, messages: list[Message], ctx: WorkflowContext[DelegationPlan]) -> None:
        user_request = _latest_message_text(messages)
        with agent_span(
            SERVICE_NAME,
            "maf.plan_delegation",
            **{
                "dem333.surface": "maf",
                "gen_ai.operation.name": "agent",
                "gen_ai.agent.name": SERVICE_NAME,
                "dem333.input_length": len(user_request),
            },
        ):
            plan = await plan_delegation(user_request)
        await ctx.send_message(DelegationPlan(user_request=user_request, plan=plan))


class SpecialistCallExecutor(Executor):
    @handler
    async def call(self, delegation: DelegationPlan, ctx: WorkflowContext[SpecialistOutputs]) -> None:
        with agent_span(
            SERVICE_NAME,
            "maf.call_specialists",
            **{
                "dem333.surface": "maf",
                "gen_ai.operation.name": "invoke_agent",
                "gen_ai.agent.name": SERVICE_NAME,
                "dem333.transport": os.getenv("DEM333_COORDINATOR_TRANSPORT", "a2a").lower(),
            },
        ):
            itinerary_text, policy_text, transport = await call_specialists(
                delegation.user_request,
                delegation.plan,
            )
        await ctx.send_message(
            SpecialistOutputs(
                user_request=delegation.user_request,
                plan=delegation.plan,
                itinerary=itinerary_text,
                policy=policy_text,
                transport=transport,
            )
        )


class ActionExecutor(Executor):
    @handler
    async def act(self, outputs: SpecialistOutputs, ctx: WorkflowContext[ActionOutputs]) -> None:
        with agent_span(
            SERVICE_NAME,
            "maf.perform_actions",
            **{
                "dem333.surface": "maf",
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.agent.name": SERVICE_NAME,
            },
        ):
            receipts = [
                await run_executive_summary_skill(
                    SERVICE_NAME,
                    outputs.user_request,
                    outputs.transport,
                ),
                await call_mcp_tool(
                    SERVICE_NAME,
                    "open_followup_task",
                    {
                        "owner": "account team",
                        "title": "Confirm DEM333 customer visit owners and trace review",
                        "due": "T-2 business days",
                    },
                ),
            ]
        await ctx.send_message(
            ActionOutputs(
                user_request=outputs.user_request,
                plan=outputs.plan,
                itinerary=outputs.itinerary,
                policy=outputs.policy,
                transport=outputs.transport,
                receipts=receipts,
            )
        )


class SynthesisExecutor(Executor):
    @handler
    async def synthesize(self, outputs: ActionOutputs, ctx: WorkflowContext[Never, str]) -> None:
        with agent_span(
            SERVICE_NAME,
            "maf.synthesize",
            **{
                "dem333.surface": "maf",
                "gen_ai.operation.name": "agent",
                "gen_ai.agent.name": SERVICE_NAME,
            },
        ):
            answer = await synthesize_answer(
                user_request=outputs.user_request,
                delegation_plan=outputs.plan,
                itinerary=outputs.itinerary,
                policy=outputs.policy,
                transport=outputs.transport,
                action_receipts=outputs.receipts,
            )
        await ctx.yield_output(answer)


def build_maf_coordinator():
    planner = DelegationPlannerExecutor(id="maf_delegation_planner")
    specialists = SpecialistCallExecutor(id="maf_specialist_calls")
    actions = ActionExecutor(id="maf_actions")
    synthesis = SynthesisExecutor(id="maf_synthesis")
    workflow = (
        WorkflowBuilder(
            name="dem333-action-coordinator",
            description=(
                "MAF workflow that plans delegation, invokes specialist agents, "
                "performs skills/MCP actions, and synthesizes the final response."
            ),
            start_executor=planner,
            output_executors=[synthesis],
        )
        .add_edge(planner, specialists)
        .add_edge(specialists, actions)
        .add_edge(actions, synthesis)
        .build()
    )
    return workflow.as_agent(name="dem333-maf-coordinator")


MAF_COORDINATOR = build_maf_coordinator()


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
        "coordinator.delegate",
        context_carrier=context.client_headers,
        **{
            "gen_ai.system": "azure.ai.foundry",
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.agent.name": SERVICE_NAME,
            "dem333.surface": "responses-protocol",
            "azure.ai.agentserver.response_id": context.response_id,
            "gen_ai.conversation.id": context.conversation_id,
            "dem333.input_length": len(user_request),
            "dem333.transport": os.getenv("DEM333_COORDINATOR_TRANSPORT", "a2a").lower(),
        },
    ):
        logger.info("Planning and calling specialist agents")
        try:
            result = await MAF_COORDINATOR.run(user_request)
            answer = (getattr(result, "text", "") or str(result)).strip()
        except (A2ACallError, SpecialistCallError) as exc:
            logger.error("Specialist call failed: %s", exc)
            answer = (
                "Coordinator could not complete delegation.\n"
                f"Failed endpoint: {exc.endpoint}\n"
                f"Error: {exc}"
            )
            return TextResponse(context, request, text=_single_chunk(answer))

    return TextResponse(context, request, text=_single_chunk(answer))


if __name__ == "__main__":
    app.run()
