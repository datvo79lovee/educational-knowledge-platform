"""Unit tests cho M2 prompt experiment; không gọi Ollama và không đọc GT."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.evaluation.run_evidence_review_prompt_experiment import (
    VARIANTS,
    build_response,
    validate_requests,
)
from src.evidence_review.contracts import ReviewerDecision
from src.evidence_review.prompts_v2 import PROMPT_VERSION, SYSTEM_PROMPT


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)


def test_prompt_v2_requires_complete_coverage() -> None:
    assert PROMPT_VERSION == "evidence_review_prompt_v2_complete_coverage"
    assert "entire question" in SYSTEM_PROMPT
    assert "every essential part" in SYSTEM_PROMPT
    assert "supports only part" in SYSTEM_PROMPT
    assert "both sides" in SYSTEM_PROMPT
    assert "outside knowledge" in SYSTEM_PROMPT
    assert "at most once" in SYSTEM_PROMPT


def test_variants_change_only_prompt_identity() -> None:
    assert [row.variant_id for row in VARIANTS] == ["control_v1", "candidate_v2"]
    assert VARIANTS[0].prompt_version == "evidence_review_prompt_v1"
    assert VARIANTS[1].prompt_version == PROMPT_VERSION


def test_request_package_has_no_ground_truth_leakage() -> None:
    requests = [
        json.loads(line)
        for line in REQUEST_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    schema = json.loads(
        (PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate_requests(requests, Draft202012Validator(schema))


def test_candidate_response_keeps_retrieval_identity_and_prompt_version() -> None:
    request = json.loads(REQUEST_FILE.read_text(encoding="utf-8").splitlines()[0])
    chosen_id = request["candidates"][0]["chunk_id"]
    response = build_response(
        request,
        ReviewerDecision(
            decision="accept",
            decision_reason="The selected excerpt covers the complete question.",
            supporting_chunk_ids=[chosen_id],
        ),
        VARIANTS[1],
    )
    assert response["retrieval_identity"] == request["retrieval_identity"]
    assert response["execution_identity"]["prompt_version"] == PROMPT_VERSION
    assert response["supporting_chunk_ids"] == [chosen_id]


def test_experiment_manifest_schema_is_valid() -> None:
    schema = json.loads(
        (
            PROJECT_ROOT
            / "schemas/evidence_review_prompt_experiment_manifest_v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
