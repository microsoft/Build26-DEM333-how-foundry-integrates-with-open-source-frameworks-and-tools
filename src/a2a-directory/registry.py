import json
import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_AGENT_CARD_PATH = "agentCard/v0.3"


@dataclass(frozen=True)
class A2AAgent:
    """Allowlisted A2A agent that Copilot can discover and call."""

    id: str
    name: str
    base_url: str
    description: str
    agent_card_path: str = DEFAULT_AGENT_CARD_PATH
    tags: tuple[str, ...] = field(default_factory=tuple)

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

        raw_tags = data.get("tags", ())
        if isinstance(raw_tags, str):
            tags = tuple(tag.strip() for tag in raw_tags.split(",") if tag.strip())
        else:
            tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())

        return cls(
            id=agent_id,
            name=name,
            base_url=base_url,
            description=str(data.get("description") or "").strip(),
            agent_card_path=str(data.get("agent_card_path") or DEFAULT_AGENT_CARD_PATH).strip(),
            tags=tags,
        )


def _default_agent_from_env() -> A2AAgent | None:
    base_url = os.getenv("FOUNDRY_A2A_URL", "").strip().rstrip("/")
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip().rstrip("/")
    hosted_agent_name = os.getenv("HOSTED_AGENT_NAME") or os.getenv(
        "FOUNDRY_A2A_AGENT_NAME", "dem333-openclaw-agent"
    )

    if not base_url and project_endpoint:
        base_url = f"{project_endpoint}/agents/{hosted_agent_name}/endpoint/protocols/a2a"
    if not base_url:
        return None

    return A2AAgent(
        id=os.getenv("FOUNDRY_A2A_AGENT_ID", hosted_agent_name),
        name=hosted_agent_name,
        base_url=base_url,
        description=os.getenv(
            "FOUNDRY_A2A_AGENT_DESCRIPTION",
            "DEM333 hosted agent for inbox triage, Work IQ Mail, Skills, Playwright, and Build session Q&A.",
        ),
        agent_card_path=os.getenv("FOUNDRY_A2A_AGENT_CARD_PATH", DEFAULT_AGENT_CARD_PATH),
        tags=tuple(
            tag.strip()
            for tag in os.getenv(
                "FOUNDRY_A2A_AGENT_TAGS", "dem333,mail,inbox,work-iq,mcp,skills,browser,build"
            ).split(",")
            if tag.strip()
        ),
    )


def load_agents() -> list[A2AAgent]:
    """Load the allowlisted A2A directory from env-backed config.

    A2A_AGENTS_JSON may contain a JSON array with entries:
    {"id": "...", "name": "...", "base_url": "...", "description": "...", "tags": [...]}
    If omitted, the existing DEM333 FOUNDRY_A2A_URL / AZURE_AI_PROJECT_ENDPOINT settings
    seed a one-agent directory.
    """

    raw_catalog = os.getenv("A2A_AGENTS_JSON")
    if raw_catalog:
        try:
            entries = json.loads(raw_catalog)
        except json.JSONDecodeError as exc:
            raise ValueError("A2A_AGENTS_JSON must be valid JSON") from exc
        if not isinstance(entries, list):
            raise ValueError("A2A_AGENTS_JSON must be a JSON array")
        agents = [A2AAgent.from_mapping(entry) for entry in entries]
    else:
        default_agent = _default_agent_from_env()
        agents = [default_agent] if default_agent else []

    if not agents:
        raise RuntimeError(
            "No A2A agents configured. Set A2A_AGENTS_JSON or FOUNDRY_A2A_URL "
            "(or AZURE_AI_PROJECT_ENDPOINT plus HOSTED_AGENT_NAME)."
        )

    ids = [agent.id for agent in agents]
    if len(ids) != len(set(ids)):
        raise ValueError("A2A agent ids must be unique")
    return agents


def find_agent(agent_id: str) -> A2AAgent:
    normalized = agent_id.strip()
    for agent in load_agents():
        if agent.id == normalized:
            return agent
    known = ", ".join(agent.id for agent in load_agents())
    raise ValueError(f"Unknown A2A agent_id {agent_id!r}. Use search_agent first. Known ids: {known}")

