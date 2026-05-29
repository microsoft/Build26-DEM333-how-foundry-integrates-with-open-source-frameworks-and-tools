from deepagents.middleware.skills import _alist_skills_with_errors
from deepagents.backends import BackendProtocol

async def inspect_loaded_skills(skill_sources: list[str], backend: BackendProtocol) -> tuple[list[str], list[str]]:
    """Return (skill_names, load_errors) using the same loader the agent uses.

    Mirrors `SkillsMiddleware.abefore_agent()` so we see exactly which skills
    the agent will have access to in `state['skills_metadata']`.
    """
    seen: dict[str, None] = {}
    errors: list[str] = []
    for source_path in skill_sources:
        source_skills, source_error = await _alist_skills_with_errors(backend, source_path)
        if source_error is not None:
            errors.append(source_error)
        for skill in source_skills:
            seen[skill["name"]] = None
    return list(seen.keys()), errors