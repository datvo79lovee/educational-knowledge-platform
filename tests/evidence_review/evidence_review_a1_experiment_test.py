"""Unit tests for A1 architecture; no Ollama calls and no evaluation labels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts.evaluation.run_evidence_review_a1_experiment import validate_requests
from src.evidence_review.a1_contracts import (
    A1EntailmentAnalysis,
    A1RequirementAnalysis,
    canonicalize_entailment_payload,
    reduce_a1_decision,
)
from src.evidence_review.a1_prompts import (
    STAGE1_SYSTEM_PROMPT,
    STAGE2_SYSTEM_PROMPT,
    build_stage1_user_prompt,
    build_stage2_output_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"


def requirement_analysis() -> A1RequirementAnalysis:
    return A1RequirementAnalysis.model_validate({
        "requirements": [
            {"requirement_id": "r1", "requirement": "Explain the first distinction."},
            {"requirement_id": "r2", "requirement": "Explain the second distinction."},
        ]
    })


def test_stage1_prompt_contains_question_only() -> None:
    payload = json.loads(build_stage1_user_prompt("What is a list?"))
    assert payload == {"question": "What is a list?"}
    lowered = STAGE1_SYSTEM_PROMPT.lower()
    assert "do not answer" in lowered
    assert "expected answers" in lowered
    assert "evidence" in lowered


def test_stage2_does_not_make_final_decision() -> None:
    lowered = STAGE2_SYSTEM_PROMPT.lower()
    assert "do not make a final accept/reject decision" in lowered
    schema = build_stage2_output_schema(["r1"], ["chunk-1"])
    assert "decision" not in json.dumps(schema)


def test_reducer_accepts_only_when_all_requirements_supported() -> None:
    analysis = requirement_analysis()
    entailment = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-2"],
                "entailment_reason": "Direct support.",
            },
            {
                "requirement_id": "r2",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            },
        ]
    })
    decision = reduce_a1_decision(analysis, entailment, ["chunk-1", "chunk-2"])
    assert decision.decision == "accept"
    assert decision.supporting_chunk_ids == ["chunk-1", "chunk-2"]


def test_reducer_accepts_assessments_in_any_order() -> None:
    analysis = requirement_analysis()
    entailment = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r2",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            },
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-2"],
                "entailment_reason": "Direct support.",
            },
        ]
    })
    decision = reduce_a1_decision(analysis, entailment, ["chunk-1", "chunk-2"])
    assert decision.decision == "accept"
    assert decision.supporting_chunk_ids == ["chunk-1", "chunk-2"]


def test_stage2_duplicate_supporting_ids_are_canonicalized_without_adding_ids() -> None:
    raw = {
        "assessments": [{
            "requirement_id": "r1",
            "supported": True,
            "supporting_chunk_ids": ["chunk-2", "chunk-1", "chunk-2"],
            "entailment_reason": "Direct support.",
        }]
    }
    canonical, duplicate_count = canonicalize_entailment_payload(raw)
    assert duplicate_count == 1
    assert canonical["assessments"][0]["supporting_chunk_ids"] == [
        "chunk-2", "chunk-1"
    ]
    assert raw["assessments"][0]["supporting_chunk_ids"] == [
        "chunk-2", "chunk-1", "chunk-2"
    ]


def test_reducer_rejects_when_one_requirement_is_unsupported() -> None:
    analysis = requirement_analysis()
    entailment = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            },
            {
                "requirement_id": "r2",
                "supported": False,
                "supporting_chunk_ids": [],
                "entailment_reason": "Not present.",
            },
        ]
    })
    decision = reduce_a1_decision(analysis, entailment, ["chunk-1", "chunk-2"])
    assert decision.decision == "reject"
    assert decision.supporting_chunk_ids == []
    assert "r2" in decision.decision_reason


def test_reducer_rejects_requirement_or_chunk_identity_drift() -> None:
    analysis = requirement_analysis()
    missing_requirement = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            }
        ]
    })
    with pytest.raises(ValueError, match="each Stage 1 requirement exactly once"):
        reduce_a1_decision(analysis, missing_requirement, ["chunk-1"])

    duplicate_requirement = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            },
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Repeated support.",
            },
        ]
    })
    with pytest.raises(ValueError, match="each Stage 1 requirement exactly once"):
        reduce_a1_decision(analysis, duplicate_requirement, ["chunk-1"])

    outside_chunk = A1EntailmentAnalysis.model_validate({
        "assessments": [
            {
                "requirement_id": "r1",
                "supported": True,
                "supporting_chunk_ids": ["outside"],
                "entailment_reason": "Direct support.",
            },
            {
                "requirement_id": "r2",
                "supported": True,
                "supporting_chunk_ids": ["chunk-1"],
                "entailment_reason": "Direct support.",
            },
        ]
    })
    with pytest.raises(ValueError, match="outside Dense Top 3"):
        reduce_a1_decision(analysis, outside_chunk, ["chunk-1"])


def test_request_package_is_frozen_and_has_no_evaluation_leakage() -> None:
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


def test_a1_schemas_are_valid_json_schema() -> None:
    for name in (
        "evidence_review_a1_requirement_analysis_v1.schema.json",
        "evidence_review_a1_entailment_v1.schema.json",
        "evidence_review_a1_experiment_manifest_v1.schema.json",
    ):
        schema = json.loads((PROJECT_ROOT / "schemas" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
