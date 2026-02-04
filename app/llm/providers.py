from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


@dataclass
class ProviderConfig:
    name: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class LLMProvider(Protocol):
    config: ProviderConfig

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ...


@dataclass
class OpenAIProvider:
    config: ProviderConfig

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.config.model or "gpt-4o-mini",
            "prompt": prompt,
            "context": context or {},
            "completion": "[stubbed OpenAI response]",
        }


@dataclass
class AnthropicProvider:
    config: ProviderConfig

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "model": self.config.model or "claude-3-haiku",
            "prompt": prompt,
            "context": context or {},
            "completion": "[stubbed Anthropic response]",
        }


@dataclass
class LocalProvider:
    config: ProviderConfig

    def generate(self, prompt: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {
            "provider": "local",
            "model": self.config.model or "local-llm",
            "prompt": prompt,
            "context": context or {},
            "completion": "[stubbed local response]",
        }
