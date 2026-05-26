from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from dem333_common.actions import ActionReceipt, receipt_to_mapping, stable_receipt_id


mcp = FastMCP("dem333-action-mcp")


def _receipt(system: str, action: str, summary: str, details: dict[str, Any]) -> dict[str, Any]:
    receipt = ActionReceipt(
        system=system,
        action=action,
        receipt_id=stable_receipt_id(action, details),
        status="completed",
        summary=summary,
        details=details,
    )
    return receipt_to_mapping(receipt)


@mcp.tool()
def reserve_demo_room(city: str, days: int, audience: str) -> dict[str, Any]:
    """Reserve the synthetic customer briefing room for the requested visit."""
    details = {"city": city, "days": days, "audience": audience}
    return _receipt(
        "mcp-demo-facilities",
        "reserve_demo_room",
        f"Reserved {city} executive briefing room for {days} day(s).",
        details,
    )


@mcp.tool()
def create_executive_brief(city: str, title: str, owner: str) -> dict[str, Any]:
    """Create the synthetic executive briefing artifact."""
    details = {"city": city, "title": title, "owner": owner}
    return _receipt(
        "mcp-demo-briefing",
        "create_executive_brief",
        f"Created briefing '{title}' for {owner}.",
        details,
    )


@mcp.tool()
def open_followup_task(owner: str, title: str, due: str) -> dict[str, Any]:
    """Open a synthetic follow-up task for the account team."""
    details = {"owner": owner, "title": title, "due": due}
    return _receipt(
        "mcp-demo-work-items",
        "open_followup_task",
        f"Opened follow-up task '{title}' for {owner}, due {due}.",
        details,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
