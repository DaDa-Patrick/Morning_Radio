"""LLM-B: Plan the show structure and music placements."""
from __future__ import annotations

from typing import Any, Dict, List

from .base import OpenAIConfig, OpenAIHelper

PLAN_PROMPT = (
    "請根據以下資訊規劃早晨節目。\n"
    "輸出段落列表，每段包含 id, title, emotion, song(可選), reason(可選)。\n"
    "以 JSON array 輸出，確保可被解析。\n"
    "輸入資料：\n{payload}"
)


def plan_program(payload: Dict[str, Any], config: OpenAIConfig) -> str:
    helper = OpenAIHelper(config)
    response = helper.complete(
        [
            {"role": "system", "content": "You are a radio program director who thinks in Mandarin."},
            {"role": "user", "content": PLAN_PROMPT.format(payload=payload)},
        ]
    )
    return response
