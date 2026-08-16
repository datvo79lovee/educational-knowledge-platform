"""Unit tests cho M2B, không gọi Ollama và không đọc Ground Truth."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from scripts.evaluation.run_evidence_review import build_response, validate_requests
from src.evidence_review.contracts import ReviewerDecision, validate_candidate_subset
from src.evidence_review.prompts import build_output_schema, build_user_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)


def sample_request() -> dict:
    return json.loads(REQUEST_FILE.read_text(encoding="utf-8").splitlines()[0])


def test_accept_and_reject_contracts() -> None:
    accepted = ReviewerDecision(
        decision="accept",
        decision_reason="Candidate one directly supports the question.",
        supporting_chunk_ids=["chunk-1"],
    )
    rejected = ReviewerDecision(
        decision="reject",
        decision_reason="No supplied candidate answers the question.",
        supporting_chunk_ids=[],
    )
    assert accepted.decision == "accept"
    assert rejected.decision == "reject"


@pytest.mark.parametrize(
    ("decision", "chunk_ids"),
    (("accept", []), ("reject", ["chunk-1"])),
)
def test_invalid_decision_shape_is_rejected(decision: str, chunk_ids: list[str]) -> None:
    with pytest.raises(ValidationError):
        ReviewerDecision(
            decision=decision,
            decision_reason="Invalid shape.",
            supporting_chunk_ids=chunk_ids,
        )


def test_outside_candidate_id_is_rejected() -> None:
    decision = ReviewerDecision(
        decision="accept",
        decision_reason="Invalid external evidence.",
        supporting_chunk_ids=["outside-top3"],
    )
    with pytest.raises(ValueError, match="outside Dense Top 3"):
        validate_candidate_subset(decision, ["chunk-1", "chunk-2", "chunk-3"])


def test_prompt_contains_only_question_and_candidate_fields() -> None:
    request = sample_request()
    prompt_payload = json.loads(build_user_prompt(request))
    assert set(prompt_payload) == {"question", "candidates"}
    assert all(
        set(candidate) == {"rank", "chunk_id", "chunk_text"}
        for candidate in prompt_payload["candidates"]
    )
    prohibited = {"expected_answer_points", "relevant_time_ranges", "answerable"}
    assert not prohibited.intersection(prompt_payload)


def test_dynamic_schema_locks_ids_to_top3() -> None:
    ids = ["chunk-1", "chunk-2", "chunk-3"]
    schema = build_output_schema(ids)
    assert schema["properties"]["supporting_chunk_ids"]["items"]["enum"] == ids


def test_full_request_package_passes_without_ground_truth_fields() -> None:
    requests = [json.loads(line) for line in REQUEST_FILE.read_text(encoding="utf-8").splitlines()]
    request_schema = json.loads(
        (PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate_requests(requests, Draft202012Validator(request_schema))


def test_response_envelope_preserves_retrieval_identity() -> None:
    request = sample_request()
    chosen_id = request["candidates"][0]["chunk_id"]
    response = build_response(
        request,
        ReviewerDecision(
            decision="accept",
            decision_reason="The first excerpt supplies direct evidence.",
            supporting_chunk_ids=[chosen_id],
        ),
    )
    assert response["retrieval_identity"] == request["retrieval_identity"]
    assert response["top3_chunk_ids"] == [
        candidate["chunk_id"] for candidate in request["candidates"]
    ]
    assert response["execution_identity"]["provider"] == "ollama"


def test_runtime_manifest_schema_is_valid() -> None:
    schema = json.loads(
        (PROJECT_ROOT / "schemas/evidence_review_runtime_manifest_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)

