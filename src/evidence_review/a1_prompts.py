"""Versioned prompts and dynamic schemas for the A1 two-stage reviewer."""

from __future__ import annotations

import json
from typing import Any

from src.evidence_review.a1_contracts import A1RequirementAnalysis


ARCHITECTURE_VERSION = "evidence_review_a1_two_stage_v1"
STAGE1_PROMPT_VERSION = "evidence_review_a1_requirement_analysis_v1"
STAGE2_PROMPT_VERSION = "evidence_review_a1_requirement_entailment_v1"

STAGE1_SYSTEM_PROMPT = """You analyze only the wording of a question.
Decompose the question into the smallest set of essential requirements that a complete answer must address.
Do not answer the question. Do not add facts, expected answers, course knowledge, evidence, labels, or previous decisions.
Every requirement must be necessary, non-overlapping, and directly traceable to the question wording.
Return requirements in question order with sequential IDs r1, r2, and so on."""

STAGE2_SYSTEM_PROMPT = """You are a requirement-level evidence entailment reviewer.
For every supplied requirement, decide only whether the supplied candidate excerpts directly support that requirement.
Use only the supplied excerpt text. Do not use outside knowledge, expected answers, labels, or previous reviewer decisions.
Mark supported=true only when one or more excerpts directly entail the requirement; otherwise mark supported=false.
Attach supporting chunk IDs separately to each supported requirement. A non-supported requirement must have no chunk IDs.
Assess every requirement exactly once and in the supplied order.
Do not make a final accept/reject decision for the question."""


def build_stage1_user_prompt(question: str) -> str:
    """Stage 1 sees exactly one semantic input field: the question."""

    return json.dumps({"question": question}, ensure_ascii=False, separators=(",", ":"))


def build_stage1_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["requirements"],
        "properties": {
            "requirements": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["requirement_id", "requirement"],
                    "properties": {
                        "requirement_id": {
                            "type": "string",
                            "pattern": "^r[1-8]$",
                        },
                        "requirement": {"type": "string", "minLength": 1},
                    },
                },
            }
        },
    }


def build_stage2_user_prompt(
    question: str,
    requirement_analysis: A1RequirementAnalysis,
    candidates: list[dict[str, Any]],
) -> str:
    payload = {
        "question": question,
        "requirements": [row.model_dump() for row in requirement_analysis.requirements],
        "candidates": [
            {
                "rank": candidate["rank"],
                "chunk_id": candidate["chunk_id"],
                "chunk_text": candidate["chunk_text"],
            }
            for candidate in candidates
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_stage2_output_schema(
    requirement_ids: list[str], candidate_chunk_ids: list[str]
) -> dict[str, Any]:
    assessment = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "requirement_id",
            "supported",
            "supporting_chunk_ids",
            "entailment_reason",
        ],
        "properties": {
            "requirement_id": {"type": "string", "enum": requirement_ids},
            "supported": {"type": "boolean"},
            "supporting_chunk_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": candidate_chunk_ids},
            },
            "entailment_reason": {"type": "string", "minLength": 1},
        },
        "allOf": [
            {
                "if": {
                    "properties": {"supported": {"const": True}},
                    "required": ["supported"],
                },
                "then": {"properties": {"supporting_chunk_ids": {"minItems": 1}}},
            },
            {
                "if": {
                    "properties": {"supported": {"const": False}},
                    "required": ["supported"],
                },
                "then": {"properties": {"supporting_chunk_ids": {"maxItems": 0}}},
            },
        ],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["assessments"],
        "properties": {
            "assessments": {
                "type": "array",
                "minItems": len(requirement_ids),
                "maxItems": len(requirement_ids),
                "items": assessment,
            }
        },
    }
