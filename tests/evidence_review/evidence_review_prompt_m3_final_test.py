"""Tests for canonicalizing and freezing final M3 prompt-experiment results."""

from __future__ import annotations

import csv
import json

import pytest

from scripts.evaluation.canonicalize_evidence_review_prompt_experiment import (
    CANONICAL_EVIDENCE_FILE,
    CANONICAL_HUMAN_FILE,
    DEFAULT_REVIEW_EXPORT,
    FINAL_METRICS_FILE,
    build,
)


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_final_m3_freezes_review_and_failed_candidate(tmp_path) -> None:
    manifest = build(DEFAULT_REVIEW_EXPORT, tmp_path)
    assert manifest["m3_status"] == "failed_candidate"
    assert manifest["ground_truth_modified"] is False
    assert manifest["prompt_or_model_modified"] is False
    assert manifest["additional_exclusions_created"] is False

    human_rows = read_csv(tmp_path / CANONICAL_HUMAN_FILE)
    evidence_rows = read_csv(tmp_path / CANONICAL_EVIDENCE_FILE)
    assert len(human_rows) == 38
    assert len(evidence_rows) == 73
    assert sum(row["human_entailment_verdict"] == "supports" for row in human_rows) == 22
    assert sum(row["human_entailment_verdict"] == "does_not_support" for row in human_rows) == 16


def test_final_m3_applies_pre_registered_thresholds(tmp_path) -> None:
    build(DEFAULT_REVIEW_EXPORT, tmp_path)
    metrics = json.loads((tmp_path / FINAL_METRICS_FILE).read_text(encoding="utf-8"))
    gate = metrics["evidence_metrics"]["candidate_v2_e2"]["same_37_decision_evaluable_questions"]
    assert gate["selected_pair_count"] == 67
    assert gate["supports_count"] == 46
    assert gate["does_not_support_count"] == 21
    assert gate["evidence_precision"] == 46 / 67
    assert metrics["threshold_status"]["evidence_threshold"]["passed"] is False
    assert set(metrics["threshold_status"]["failed_thresholds"]) == {
        "false_accept_rate",
        "evidence_selection_precision",
    }


def test_final_m3_rejects_immutable_field_change(tmp_path) -> None:
    payload = json.loads(DEFAULT_REVIEW_EXPORT.read_text(encoding="utf-8"))
    payload["review_rows"][0]["question"] = "changed"
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Immutable review field changed"):
        build(changed, tmp_path / "out")


def test_final_m3_needs_discussion_blocks_gate(tmp_path) -> None:
    payload = json.loads(DEFAULT_REVIEW_EXPORT.read_text(encoding="utf-8"))
    payload["review_rows"][0]["human_entailment_verdict"] = "needs_discussion"
    changed = tmp_path / "needs_discussion.json"
    changed.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="needs_discussion blocks final gate"):
        build(changed, tmp_path / "out")
