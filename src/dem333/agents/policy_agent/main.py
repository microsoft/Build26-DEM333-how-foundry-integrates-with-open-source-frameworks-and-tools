import asyncio
import logging

from azure.ai.agentserver.responses import (
    CreateResponse,
    ResponseContext,
    ResponsesAgentServerHost,
    ResponsesServerOptions,
    TextResponse,
)
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from dem333_common.llm import get_chat_model
from dem333_common.actions import format_receipts
from dem333_common.skills import run_policy_review_skill, run_readiness_checklist_skill
from dem333_common.telemetry import agent_span, configure_observability
from dem333_common.text import detect_industry


SERVICE_NAME = "dem333-policy-agent"
logger = logging.getLogger(SERVICE_NAME)

load_dotenv(override=False)
configure_observability(SERVICE_NAME)

app = ResponsesAgentServerHost(
    options=ResponsesServerOptions(default_fetch_history_count=10)
)


async def build_policy_guidance(user_request: str) -> str:
    industry = detect_industry(user_request)
    analyst = get_chat_model(temperature=0.1, max_completion_tokens=450)
    drafter = get_chat_model(temperature=0.2, max_completion_tokens=550)

    risk_response = await analyst.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a Microsoft policy risk analyst for customer-facing executive briefings. "
                    "Identify compliance, privacy, accessibility, procurement, and commitment risks. "
                    "Return concise bullets grouped by severity."
                )
            ),
            HumanMessage(
                content=(
                    f"Industry hint: {industry}\n"
                    f"Customer visit request:\n{user_request}\n\n"
                    "Analyze the risks and explain what evidence a human owner should review."
                )
            ),
        ],
        config={"metadata": {"agent_name": "policy-risk-analysis", "dem333.step": "risk-analysis"}},
    )
    risk_analysis = str(risk_response.content)

    guidance_response = await drafter.ainvoke(
        [
            SystemMessage(
                content=(
                    "You write practical guardrails for account teams. Be specific, demo-safe, and concise. "
                    "Include a final 'Human review checklist' section."
                )
            ),
            HumanMessage(
                content=(
                    f"Customer industry: {industry}\n"
                    f"Original request:\n{user_request}\n\n"
                    f"Risk analysis from the policy analyst:\n{risk_analysis}\n\n"
                    "Draft policy guidance that the coordinator can attach to a proposed itinerary."
                )
            ),
        ],
        config={"metadata": {"agent_name": "policy-guidance-draft", "dem333.step": "guidance-draft"}},
    )
    guidance = str(guidance_response.content)
    skill_receipts = [
        await run_policy_review_skill(SERVICE_NAME, industry, risk_analysis),
        await run_readiness_checklist_skill(SERVICE_NAME, industry, guidance),
    ]

    return (
        f"Policy specialist LLM analysis for a {industry} customer:\n"
        f"{risk_analysis}\n\n"
        f"Policy specialist guidance:\n{guidance}\n\n"
        f"{format_receipts(skill_receipts, 'Policy actions performed through Agent Framework skills')}"
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
            "dem333.surface": "responses-protocol",
            "azure.ai.agentserver.response_id": context.response_id,
            "gen_ai.conversation.id": context.conversation_id,
            "dem333.input_length": len(user_request),
        },
    ):
        logger.info("Evaluating policy guidance")
        answer = await build_policy_guidance(user_request)
    return TextResponse(context, request, text=_single_chunk(answer))


if __name__ == "__main__":
    app.run()
