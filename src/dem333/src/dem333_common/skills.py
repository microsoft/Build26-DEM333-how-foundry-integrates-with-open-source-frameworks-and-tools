from __future__ import annotations

from agent_framework import InlineSkill, SkillFrontmatter
from opentelemetry import trace

from dem333_common.actions import ActionReceipt, stable_receipt_id


POLICY_REVIEW_SKILL = InlineSkill(
    frontmatter=SkillFrontmatter(
        name="policy-review",
        description="Creates the human compliance review action for a customer briefing.",
        metadata={"dem333.surface": "skill"},
    ),
    instructions=(
        "Review privacy, accessibility, procurement, and customer-commitment risks. "
        "Create a concise action receipt for the human accountable owner."
    ),
)

READINESS_CHECKLIST_SKILL = InlineSkill(
    frontmatter=SkillFrontmatter(
        name="readiness-checklist",
        description="Creates the demo readiness checklist action for the account team.",
        metadata={"dem333.surface": "skill"},
    ),
    instructions=(
        "Turn specialist findings into a short readiness checklist with owners and "
        "a stage-safe demo validation step."
    ),
)

EXECUTIVE_SUMMARY_SKILL = InlineSkill(
    frontmatter=SkillFrontmatter(
        name="executive-summary",
        description="Creates the coordinator action receipt for the final briefing pack.",
        metadata={"dem333.surface": "skill"},
    ),
    instructions="Create the executive summary action after specialists finish.",
)


def _run_skill_span(service_name: str, skill_name: str, payload: dict[str, str]) -> ActionReceipt:
    receipt_id = stable_receipt_id(skill_name, payload)
    tracer = trace.get_tracer(service_name)
    with tracer.start_as_current_span("skill.run") as span:
        span.set_attribute("dem333.surface", "skill")
        span.set_attribute("agent_framework.skill.name", skill_name)
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("gen_ai.tool.name", skill_name)
        span.set_attribute("dem333.action.receipt_id", receipt_id)
        for key, value in payload.items():
            span.set_attribute(f"dem333.skill.{key}", value[:500])

    return ActionReceipt(
        system="agent-framework-skill",
        action=skill_name,
        receipt_id=receipt_id,
        status="created",
        summary=payload["summary"],
        details=payload,
    )


async def run_policy_review_skill(service_name: str, industry: str, risk_analysis: str) -> ActionReceipt:
    return _run_skill_span(
        service_name,
        POLICY_REVIEW_SKILL.frontmatter.name,
        {
            "industry": industry,
            "summary": f"Opened human policy review for {industry} customer risks.",
            "evidence": risk_analysis[:500],
        },
    )


async def run_readiness_checklist_skill(service_name: str, industry: str, guidance: str) -> ActionReceipt:
    return _run_skill_span(
        service_name,
        READINESS_CHECKLIST_SKILL.frontmatter.name,
        {
            "industry": industry,
            "summary": f"Created readiness checklist for {industry} briefing owners.",
            "guidance": guidance[:500],
        },
    )


async def run_executive_summary_skill(service_name: str, user_request: str, transport: str) -> ActionReceipt:
    return _run_skill_span(
        service_name,
        EXECUTIVE_SUMMARY_SKILL.frontmatter.name,
        {
            "transport": transport,
            "summary": f"Prepared executive summary packet after {transport} specialist delegation.",
            "request": user_request[:500],
        },
    )
