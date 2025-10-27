"""LLM-C: generate SSML broadcast script."""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import OpenAIConfig, OpenAIHelper, build_system_prompt

SCRIPT_PROMPT = (
    "你是一位早晨電台主持人，根據段落規劃與角色設定，"
    "請輸出一份完整逐字稿（SSML 格式），包含語氣、停頓與音樂插入點。\n"
    "節目規劃：\n{plan}\n"
    "角色設定：\n{persona}\n"
    "請直接輸出 <speak> ... </speak>。"
)


def generate_script(plan: Any, persona: Dict[str, Any], config: OpenAIConfig) -> str:
    helper = OpenAIHelper(config)
    system_prompt = build_system_prompt(persona)
    prompt = SCRIPT_PROMPT.format(plan=json.dumps(plan, ensure_ascii=False, indent=2), persona=json.dumps(persona, ensure_ascii=False))
    response = helper.complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
    )
    return response
