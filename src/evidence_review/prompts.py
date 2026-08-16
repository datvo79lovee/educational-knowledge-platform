"""Prompt versioned, không chứa Ground Truth hay expected answer points."""

from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "evidence_review_prompt_v1"

SYSTEM_PROMPT = """You are an evidence sufficiency reviewer.
Decide whether the supplied candidate excerpts are sufficient to answer the question using only their text.
Do not use outside knowledge. Do not invent facts. Do not request or assume any excerpt outside the supplied candidates.
Return accept only when at least one supplied excerpt directly supports a grounded answer. Return reject otherwise.
For accept, supporting_chunk_ids must contain only the supplied chunk IDs that directly support the answer.
For reject, supporting_chunk_ids must be empty.
Keep decision_reason concise and refer only to the supplied evidence."""


def build_user_prompt(request: dict[str, Any]) -> str:
    """Chỉ serialize question và Dense Top 3, loại metadata không cần thiết."""

    payload = {
        "question": request["question"],
        "candidates": [
            {
                "rank": candidate["rank"],
                "chunk_id": candidate["chunk_id"],
                "chunk_text": candidate["chunk_text"],
            }
            for candidate in request["candidates"]
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_output_schema(candidate_chunk_ids: list[str]) -> dict[str, Any]:
    """Khóa ID model có thể sinh vào đúng candidate pool hiện tại."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "decision_reason", "supporting_chunk_ids"],
        "properties": {
            "decision": {"type": "string", "enum": ["accept", "reject"]},
            "decision_reason": {"type": "string", "minLength": 1},
            "supporting_chunk_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": candidate_chunk_ids},
            },
        },
    }

