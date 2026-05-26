from __future__ import annotations

import os
from functools import lru_cache

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required for LLM-backed DEM333 agents")
    return value


@lru_cache(maxsize=16)
def get_chat_model(
    *,
    temperature: float = 0.2,
    max_completion_tokens: int = 500,
) -> AzureChatOpenAI:
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    )
    deployment_name = _required_env("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    return AzureChatOpenAI(
        azure_endpoint=_required_env("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=deployment_name,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
        azure_ad_token_provider=token_provider,
        model=os.getenv("AZURE_OPENAI_MODEL_NAME", deployment_name),
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        timeout=30,
        max_retries=2,
    )
