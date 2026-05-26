from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionReceipt:
    system: str
    action: str
    receipt_id: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def stable_receipt_id(prefix: str, payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{digest}"


def receipt_from_mapping(payload: dict[str, Any]) -> ActionReceipt:
    return ActionReceipt(
        system=str(payload["system"]),
        action=str(payload["action"]),
        receipt_id=str(payload["receipt_id"]),
        status=str(payload["status"]),
        summary=str(payload["summary"]),
        details=dict(payload.get("details") or {}),
    )


def receipt_to_mapping(receipt: ActionReceipt) -> dict[str, Any]:
    return {
        "system": receipt.system,
        "action": receipt.action,
        "receipt_id": receipt.receipt_id,
        "status": receipt.status,
        "summary": receipt.summary,
        "details": receipt.details,
    }


def format_receipts(receipts: list[ActionReceipt], heading: str = "Actions performed") -> str:
    if not receipts:
        return f"{heading}:\n- None"
    lines = [f"{heading}:"]
    for receipt in receipts:
        lines.append(
            f"- [{receipt.status}] {receipt.action} via {receipt.system} "
            f"({receipt.receipt_id}): {receipt.summary}"
        )
    return "\n".join(lines)
