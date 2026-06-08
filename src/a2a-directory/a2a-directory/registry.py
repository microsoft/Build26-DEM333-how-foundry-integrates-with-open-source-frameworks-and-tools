import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_AGENT_CARD_PATH = "agentCard/v0.3"
DEFAULT_AGENTS_FILE = "directory.json"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class A2AAgent:
    """Allowlisted A2A agent that Copilot can discover and call."""

    id: str
    name: str
    base_url: str
    agent_card_path: str = DEFAULT_AGENT_CARD_PATH

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "A2AAgent":
        try:
            agent_id = str(data["id"]).strip()
            name = str(data.get("name") or agent_id).strip()
            base_url = str(data["base_url"]).strip().rstrip("/")
        except KeyError as exc:
            raise ValueError(f"A2A agent entry missing required field: {exc.args[0]}") from exc

        if not agent_id:
            raise ValueError("A2A agent entry id cannot be empty")
        if not base_url:
            raise ValueError(f"A2A agent entry {agent_id!r} base_url cannot be empty")

        return cls(
            id=agent_id,
            name=name,
            base_url=base_url,
            agent_card_path=str(data.get("agent_card_path") or DEFAULT_AGENT_CARD_PATH).strip(),
        )


def _load_agents_from_file(path: Path) -> list[A2AAgent] | None:
    if not path.exists():
        return None

    try:
        contents = path.read_text(encoding="utf-8")
        entries = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} must contain valid JSON") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to read A2A agents file at {path}") from exc

    agents: list[A2AAgent] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{entry!r} entry at index {index} must be a JSON object")
        agents.append(A2AAgent.from_mapping(entry))
    return agents


def _resolve_agents_file_path(configured_path: str) -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    if not configured_path:
        return (base_dir / DEFAULT_AGENTS_FILE).resolve()

    candidate = Path(configured_path).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()

def _agent_matches(query: str, card_summary: dict[str, Any]) -> bool:
    if not query:
        return True
    terms = [term for term in query.lower().split() if term]
    if not terms:
        return True

    haystack = json.dumps(card_summary, ensure_ascii=False).lower()
    # Match any term so multi-word queries still return useful candidates.
    return any(term in haystack for term in terms)


def _card_summary(agent_card: Any) -> dict[str, Any]:
    skills = []
    for skill in getattr(agent_card, "skills", []) or []:
        skills.append(
            {
                "id": getattr(skill, "id", None),
                "name": getattr(skill, "name", None),
                "description": getattr(skill, "description", None),
                "tags": list(getattr(skill, "tags", []) or []),
            }
        )
    return {
        "name": getattr(agent_card, "name", None),
        "description": getattr(agent_card, "description", None),
        "skills": skills,
    }

def load_agents() -> list[A2AAgent]:
    """Load the allowlisted A2A directory from file config.

    Uses A2A_AGENTS_FILE when set, otherwise defaults to
    project-level src/a2a-directory/directory.json.
    """
    configured_path = os.getenv("A2A_AGENTS_FILE", "").strip()
    agents_file = _resolve_agents_file_path(configured_path)
    agents = _load_agents_from_file(agents_file)

    if agents is None:
        raise RuntimeError(
            "No A2A agents configured. Provide agents via A2A_AGENTS_FILE "
            f"(default: {_resolve_agents_file_path('')}). "
            f"Load source attempted: file {agents_file} (not found)."
        )

    # Ensure all agent IDs are unique
    ids = [agent.id for agent in agents]
    if len(ids) != len(set(ids)):
        raise ValueError(f"A2A agent ids must be unique (loaded from file {agents_file})")

    return agents

def get_agent(agent_id: str) -> A2AAgent:
    """Get an A2A agent by its ID.

    Args:
        agent_id: The ID of the agent to retrieve.

    Returns:
        The A2A agent with the specified ID.

    Raises:
        ValueError: If the agent ID is not found.
    """
    normalized = agent_id.strip()
    agents = load_agents()
    for agent in agents:
        if agent.id == normalized:
            return agent
    known = ", ".join(agent.id for agent in agents)
    raise ValueError(f"Unknown A2A agent_id {agent_id!r}. Use search_agent first. Known ids: {known}")


async def search_agents(query: str = "") -> list[dict[str, Any]]:
    """Search the configured A2A agent directory.

    Returns allowlisted agent IDs that can be passed to call_agent_a2a.
    Includes entries for agent-card lookup failures so callers can detect
    attempted agents that were unavailable.
    """

    # Imported lazily to avoid a circular import (client imports from registry).
    from .client import get_agent_card

    results: list[dict[str, Any]] = []
    for agent in load_agents():
        try:
            card = _card_summary(await get_agent_card(agent))
        except Exception as exc:
            logger.exception(
                "Failed to retrieve agent card for agent_id=%s from %s",
                agent.id,
                agent.base_url,
            )
            results.append(
                {
                    "agent_id": agent.id,
                    "status": "agent_card_lookup_failed",
                    "agent_card": None,
                    "error": str(exc),
                    "base_url": agent.base_url,
                }
            )
            continue

        if _agent_matches(query, card):
            results.append(
                {
                    "agent_id": agent.id,
                    "status": "ok",
                    "agent_card": card,
                }
            )
    return results

