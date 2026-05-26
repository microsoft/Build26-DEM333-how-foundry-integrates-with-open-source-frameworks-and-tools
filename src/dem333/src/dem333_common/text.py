from __future__ import annotations

import re


def first_match(text: str, pattern: str, default: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return default
    return match.group(1).strip()


def detect_city(text: str) -> str:
    for city in ("Seattle", "San Francisco", "New York", "London", "Paris", "Tokyo"):
        if city.lower() in text.lower():
            return city
    return first_match(text, r"\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "Seattle")


def detect_days(text: str, default: int = 2) -> int:
    match = re.search(r"\b(\d+)\s*[- ]?day", text, re.IGNORECASE)
    if not match:
        return default
    return max(1, min(int(match.group(1)), 5))


def detect_industry(text: str) -> str:
    lowered = text.lower()
    if "health" in lowered:
        return "healthcare"
    if "finance" in lowered or "bank" in lowered:
        return "financial services"
    if "government" in lowered or "public sector" in lowered:
        return "public sector"
    return "enterprise"
