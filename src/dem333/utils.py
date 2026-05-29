from typing import Any

from deepagents.middleware.skills import SkillsMiddleware, _alist_skills_with_errors
from langgraph.graph.state import CompiledStateGraph


def _get_middleware(agent: CompiledStateGraph, mw_class: type) -> Any | None:
    for spec in agent.builder.nodes.values():
        runnable = getattr(spec, "runnable", spec)
        for attr in ("func", "afunc"):
            fn = getattr(runnable, attr, None)
            owner = getattr(fn, "__self__", None)
            if isinstance(owner, mw_class):
                return owner
    return None


async def inspect_loaded_skills(agent: CompiledStateGraph) -> tuple[list[str], list[str]]:
    """Inspect the skills loaded by the agent.
    
    WARNING: This function is not guaranteed to find the correct skills in all cases.
    It's provided as a learning convenience, not a production solution. DO NOT USE.
    """
    skills_mw = _get_middleware(agent, SkillsMiddleware)
    if skills_mw is None:
        return [], []

    backend = skills_mw._backend
    if callable(backend):
        return [], ["Backend is a factory; cannot resolve without a runtime."]

    seen: dict[str, None] = {}
    errors: list[str] = []
    for source_path in skills_mw.sources:
        source_skills, source_error = await _alist_skills_with_errors(backend, source_path)
        if source_error is not None:
            errors.append(source_error)
        for skill in source_skills:
            seen[skill["name"]] = None
    return list(seen.keys()), errors