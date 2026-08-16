"""Tests cho M3 metrics và ranh giới human review."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.evaluation.canonicalize_evidence_reviewer_review import (
    expected_classification,
    expected_from_sufficiency,
)

from scripts.evaluation.evaluate_evidence_reviewer import (
    EVIDENCE_AUDIT_FILE,
    HUMAN_REVIEW_FILE,
    STRICT_RESULTS_FILE,
    build,
    strict_classification,
)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_strict_classification_abcd_and_out_of_scope() -> None:
    assert strict_classification(expected="accept", predicted="accept", answerable=True) == "A_success_decision"
    assert strict_classification(expected="accept", predicted="reject", answerable=True) == "B_reviewer_false_reject"
    assert strict_classification(expected="reject", predicted="reject", answerable=True) == "C_correct_abstention_retrieval_limit"
    assert strict_classification(expected="reject", predicted="accept", answerable=True) == "D_potential_false_accept"
    assert strict_classification(expected="reject", predicted="reject", answerable=False) == "out_of_scope_correct_reject"


def test_build_preserves_pending_human_labels(tmp_path) -> None:
    manifest = build(tmp_path)
    assert manifest["strict_metrics"]["confusion_matrix"] == {
        "tp": 13,
        "fp": 7,
        "fn": 3,
        "tn": 5,
    }
    assert manifest["m3_status"] == "human_review_pending"
    human_rows = read_csv(tmp_path / HUMAN_REVIEW_FILE)
    assert len(human_rows) == 12
    assert {
        row["question_id"] for row in human_rows if row["audit_flag"]
    } == {"mit60001-q-023", "mit60001-q-041"}
    assert all(row["human_review_status"] == "pending" for row in human_rows)
    assert all(row["human_final_classification"] == "" for row in human_rows)


def test_build_separates_strict_and_evidence_audit(tmp_path) -> None:
    build(tmp_path)
    strict_rows = read_csv(tmp_path / STRICT_RESULTS_FILE)
    evidence_rows = read_csv(tmp_path / EVIDENCE_AUDIT_FILE)
    assert len(strict_rows) == 28
    assert len(evidence_rows) == 35
    assert all(row["human_entailment_verdict"] == "" for row in evidence_rows)
    assert sum(row["auto_gt_time_overlap"] == "True" for row in evidence_rows) == 19


def test_metrics_json_is_not_used_as_reviewer_input(tmp_path) -> None:
    build(tmp_path)
    manifest = json.loads(
        (tmp_path / "reports/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_pre_review_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["human_review"]["status"] == "pending"
    assert manifest["strict_metrics"]["evidence_entailment_status"] == "human_review_pending"


def test_human_sufficiency_maps_to_expected_decision_without_forcing_exclusions() -> None:
    assert expected_from_sufficiency("sufficient") == "accept"
    assert expected_from_sufficiency("insufficient") == "reject"
    assert expected_from_sufficiency("needs_discussion") is None
    assert expected_from_sufficiency("possible_gt_under_credit") is None


def test_human_classification_mapping() -> None:
    assert expected_classification("accept", "accept") == "A_success"
    assert expected_classification("accept", "reject") == "B_reviewer_false_reject"
    assert expected_classification("reject", "reject") == "C_correct_abstention"
    assert expected_classification("reject", "accept") == "D_potential_false_accept"


def test_final_canonical_artifacts_preserve_exclusions() -> None:
    project_root = Path(__file__).resolve().parents[2]
    final_rows = read_csv(
        project_root / "reports/15_evidence_reviewer_evaluation/final_decision_results.csv"
    )
    excluded = {row["question_id"] for row in final_rows if row["evaluation_status"] == "excluded"}
    assert excluded == {"mit60001-q-017", "mit60001-q-023", "mit60001-q-041"}
