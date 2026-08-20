"""Tests for the frozen, no-model A1 M3 evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.evaluation.evaluate_evidence_review_a1 import build_evaluation, divide_or_none


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_divide_or_none_does_not_turn_zero_over_zero_into_perfect_precision() -> None:
    assert divide_or_none(0, 0) is None
    assert divide_or_none(0, 16) == 0.0


def test_a1_m3_decision_metrics_are_for_the_frozen_37_question_scope() -> None:
    metrics = build_evaluation()["metrics"]["decision_metrics"]
    assert metrics["confusion_matrix"] == {"tp": 0, "fp": 0, "fn": 21, "tn": 16}
    assert metrics["accept_recall"] == 0.0
    assert metrics["false_accept_rate"] == 0.0
    assert metrics["accept_precision"] is None


def test_a1_m3_evidence_precision_is_not_evaluable_without_selected_pairs() -> None:
    evidence = build_evaluation()["metrics"]["evidence_selection"]
    assert evidence["selected_pair_count"] == 0
    assert evidence["evidence_precision"] is None
    assert evidence["metric_status"] == "not_evaluable_zero_selected_pairs"
    assert evidence["stage2_requirement_ids_included"] is False


def test_a1_stage2_ids_remain_internal_debug_data() -> None:
    audit = build_evaluation()["internal_audit"]
    assert audit["requirement_assessment_count"] == 103
    assert audit["supported_requirement_count"] == 21
    assert audit["unsupported_requirement_count"] == 82
    assert audit["questions_with_at_least_one_supported_requirement"] == 20
    assert audit["questions_with_all_requirements_supported"] == 0
    assert audit["final_selected_pair_metric_includes_internal_ids"] is False


def test_a1_m3_manifest_schema_is_valid() -> None:
    schema = json.loads(
        (PROJECT_ROOT / "schemas/evidence_review_a1_m3_final_manifest_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
