"""Prompt v1 tối giản cho one-call grounded generation + abstention."""

from __future__ import annotations

import json
from typing import Any


PROMPT_VERSION = "grounded_answer_prompt_v1"
VI_PROMPT_VERSION = "grounded_answer_prompt_vi_v2"

SYSTEM_PROMPT = """You are a grounded answer generator for the MIT 6.0001 course.
Use only information directly supported by the three candidate excerpts.
If the excerpts cannot support a complete answer to the essential question, abstain.
For an answer, select only the chunk IDs that directly support the answer.
Do not use outside knowledge. Do not create URLs, timestamps, or citations.
Return only JSON matching the supplied schema."""

# The instruction is conditional on the decision. The previous unconditional form could
# create conflicting instructions on the abstain branch, where writing an answer cannot
# satisfy the strict contract; whether it caused the observed failures is untested.
# SYSTEM_PROMPT itself stays byte-identical to the frozen English v1.
VI_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\nIf you answer, write the answer field in Vietnamese."
    "\nIf you abstain, set answer to null and supporting_chunk_ids to an empty list."
)


def build_user_prompt(question: str, candidates: list[dict[str, Any]], answer_language: str) -> str:
    """Chỉ đưa question, retrieval rank, chunk ID và transcript text vào model."""

    evidence = [
        {
            "rank": candidate["rank"],
            "chunk_id": candidate["chunk_id"],
            "excerpt": candidate["chunk_text"],
        }
        for candidate in candidates
    ]
    prefix = "Question:\n" if answer_language == "en" else "Answer language: vi\nQuestion:\n"
    return (
        prefix + question
        + "\n\nCandidate excerpts:\n"
        + json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    )
