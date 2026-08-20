"""Tests cho M3 prompt experiment trước human evidence review."""

from __future__ import annotations

import csv
import json

from scripts.evaluation.evaluate_evidence_review_prompt_experiment import (
    DECISION_DELTA_FILE,
    EVIDENCE_AUDIT_FILE,
    PENDING_EVIDENCE_FILE,
    build,
)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_m3_uses_same_37_labels_and_three_exclusions(tmp_path) -> None:
    manifest = build(tmp_path)
    assert manifest["evaluation_scope"] == {
        "total_question_count": 40,
        "evaluated_question_count": 37,
        "excluded_question_ids": [
            "mit60001-q-017",
            "mit60001-q-023",
            "mit60001-q-041",
        ],
    }
    assert manifest["additional_exclusions_created"] is False


def test_e0_reproduces_locked_baseline_metrics(tmp_path) -> None:
    manifest = build(tmp_path)
    e0 = manifest["decision_metrics"]["locked_baseline_e0"]
    assert e0["confusion_matrix"] == {"tp": 17, "fp": 9, "fn": 4, "tn": 7}
    assert e0["question_count"] == 37


def test_six_decision_deltas_are_audited(tmp_path) -> None:
    build(tmp_path)
    rows = read_csv(tmp_path / DECISION_DELTA_FILE)
    assert len(rows) == 6
    assert {row["question_id"] for row in rows} == {
        "mit60001-q-001",
        "mit60001-q-009",
        "mit60001-q-014",
        "mit60001-q-019",
        "mit60001-q-021",
        "mit60001-q-023",
    }


def test_new_evidence_verdicts_remain_pending(tmp_path) -> None:
    manifest = build(tmp_path)
    audit_rows = read_csv(tmp_path / EVIDENCE_AUDIT_FILE)
    pending_rows = read_csv(tmp_path / PENDING_EVIDENCE_FILE)
    assert len(audit_rows) == 73
    assert len(pending_rows) == 38
    assert all(row["human_entailment_verdict"] == "" for row in pending_rows)
    assert all(row["human_review_status"] == "pending" for row in pending_rows)
    assert manifest["m3_status"] == "human_evidence_review_pending"


def test_pre_registered_thresholds_are_not_forced_complete(tmp_path) -> None:
    manifest = build(tmp_path)
    status = manifest["threshold_status"]
    assert status["evidence_threshold"]["passed"] is None
    assert status["overall"] == "human_evidence_review_pending"
    assert manifest["ground_truth_modified"] is False
    assert manifest["prompt_or_model_modified"] is False


def test_manifest_schema_is_valid_json(tmp_path) -> None:
    manifest = build(tmp_path)
    json.dumps(manifest)
