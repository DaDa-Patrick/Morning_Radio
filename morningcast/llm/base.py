"""Shared OpenAI helper utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from openai import OpenAI


@dataclass(slots=True)
class OpenAIConfig:
    api_key: str
    model: str
    temperature: float = 0.7


class OpenAIHelper:
    """Thin wrapper around the OpenAI responses API."""

    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client = OpenAI(api_key=config.api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, messages: Iterable[Dict[str, Any]], **kwargs: Any) -> str:
        params = {
            "model": self.config.model,
            "messages": list(messages),
            "temperature": self.config.temperature,
        }
        params.update(kwargs)
        response = self._client.chat.completions.create(**params)
        return response.choices[0].message.content or ""


def build_system_prompt(persona: Optional[Dict[str, Any]] = None) -> str:
    if not persona:
        return "You are a helpful radio script writer."
    name = persona.get("name", "MorningCast Host")
    tone = persona.get("tone", "warm and witty")
    favorites = ", ".join(persona.get("favorites", []))
    language_mix = persona.get("language_mix", "Chinese")
    details = [
        f"Name: {name}",
        f"Tone: {tone}",
        f"Preferred language mix: {language_mix}",
    ]
    if favorites:
        details.append(f"Music preferences: {favorites}")
    return "\n".join(["You are the persona described below:"] + details)
