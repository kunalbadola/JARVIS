from __future__ import annotations

import os
from typing import Dict

from app.llm.providers import AnthropicProvider, LocalProvider, OpenAIProvider, ProviderConfig


def load_provider_configs() -> Dict[str, ProviderConfig]:
    return {
        "openai": ProviderConfig(
            name="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        "anthropic": ProviderConfig(
            name="anthropic",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku"),
        ),
        "local": ProviderConfig(
            name="local",
            api_key=os.getenv("LOCAL_API_KEY"),
            base_url=os.getenv("LOCAL_BASE_URL"),
            model=os.getenv("LOCAL_MODEL", "local-llm"),
        ),
    }


def get_provider(name: str):
    configs = load_provider_configs()
    config = configs.get(name, configs["local"])
    if config.name == "openai":
        return OpenAIProvider(config)
    if config.name == "anthropic":
        return AnthropicProvider(config)
    return LocalProvider(config)
