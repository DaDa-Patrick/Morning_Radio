"""LLM-A: refine structured data into spoken lines."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .base import OpenAIConfig, OpenAIHelper

PROMPT_TEMPLATE = (
    "你是溫暖幽默的電台撰稿員。\n"
    "請將以下資料改寫成可口語播報的一句話，保持生活化語氣。\n"
    "輸入：\n{input}\n"
    "輸出：\n以 JSON 格式回傳，包含 spoken_line 欄位。"
)


def refine_items(items: Iterable[Dict[str, Any]], config: OpenAIConfig) -> List[str]:
    helper = OpenAIHelper(config)
    spoken_lines: List[str] = []
    for item in items:
        user_prompt = PROMPT_TEMPLATE.format(input=item)
        response = helper.complete(
            [
                {"role": "system", "content": "You are a Taiwanese Mandarin radio copywriter."},
                {"role": "user", "content": user_prompt},
            ]
        )
        spoken_lines.append(response.strip())
    return spoken_lines
