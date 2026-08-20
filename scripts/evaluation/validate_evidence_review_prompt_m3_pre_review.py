"""Validate frozen M3 pre-review artifacts without calling a model."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_FILE = PROJECT_ROOT / (
    "reports/17_evidence_reviewer_prompt_evaluation/m3_pre_review_manifest.json"
)
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / (
    "schemas/evidence_review_prompt_m3_pre_review_manifest_v1.schema.json"
)
METRICS_FILE = PROJECT_ROOT / (
    "reports/17_evidence_reviewer_prompt_evaluation/pre_review_decision_metrics.json"
)
DELTA_FILE = PROJECT_ROOT / (
    "reports/17_evidence_reviewer_prompt_evaluation/decision_delta_audit.csv"
)
EVIDENCE_AUDIT_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_evidence_selection_audit.csv"
)
PENDING_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_pending_evidence_review.csv"
)
WORKBOOK_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/outputs/phase8_m3/phase8_m3_prompt_experiment_evidence_review.xlsx"
)

INPUT_FILES = {
    "baseline_final_manifest": PROJECT_ROOT
    / "reports/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_manifest.json",
    "canonical_decisions": PROJECT_ROOT
    / "reports/15_evidence_reviewer_evaluation/final_decision_results.csv",
    "canonical_evidence": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/m3_evidence_entailment_canonical.csv",
    "e0_locked_baseline": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl",
    "e1_current_control": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/control_v1_reviews.jsonl",
    "e2_candidate_v2": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl",
    "evaluator": PROJECT_ROOT
    / "scripts/evaluation/evaluate_evidence_review_prompt_experiment.py",
    "experiment_manifest": PROJECT_ROOT
    / "reports/16_evidence_reviewer_prompt_experiment/prompt_experiment_manifest.json",
    "ground_truth": PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl",
    "manifest_schema": MANIFEST_SCHEMA_FILE,
    "mechanical_comparison": PROJECT_ROOT
    / "reports/16_evidence_reviewer_prompt_experiment/mechanical_comparison.json",
    "request_package": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl",
    "thresholds": PROJECT_ROOT
    / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_thresholds.json",
}


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"M3 manifest schema failed: {errors[0].message}")
    actual_inputs = {
        label: sha256_file(path) for label, path in sorted(INPUT_FILES.items())
    }
    if manifest["input_sha256"] != actual_inputs:
        raise ValueError("M3 frozen input hash mismatch")

    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    if manifest["decision_metrics"] != metrics["decision_metrics"]:
        raise ValueError("M3 decision metrics mismatch")
    if metrics["evaluation_scope"] != manifest["evaluation_scope"]:
        raise ValueError("M3 evaluation scope mismatch")
    e0 = metrics["decision_metrics"]["locked_baseline_e0"]
    if e0["confusion_matrix"] != {"tp": 17, "fp": 9, "fn": 4, "tn": 7}:
        raise ValueError("Locked E0 baseline was not reproduced")
    e2 = metrics["decision_metrics"]["candidate_v2_e2"]
    if e2["false_accept_rate"] != 0.5625:
        raise ValueError("Frozen E2 FAR drift")

    delta_rows = load_csv(DELTA_FILE)
    expected_delta_ids = {
        "mit60001-q-001",
        "mit60001-q-009",
        "mit60001-q-014",
        "mit60001-q-019",
        "mit60001-q-021",
        "mit60001-q-023",
    }
    if len(delta_rows) != 6 or {row["question_id"] for row in delta_rows} != expected_delta_ids:
        raise ValueError("Six-decision delta audit drift")
    evidence_rows = load_csv(EVIDENCE_AUDIT_FILE)
    pending_rows = load_csv(PENDING_FILE)
    if len(evidence_rows) != 73 or len(pending_rows) != 38:
        raise ValueError("Evidence audit count drift")
    if sum(row["human_review_status"] == "canonical_reuse" for row in evidence_rows) != 35:
        raise ValueError("Canonical evidence reuse count drift")
    if any(
        row["human_entailment_verdict"] or row["human_review_status"] != "pending"
        for row in pending_rows
    ):
        raise ValueError("Pending evidence rows contain fabricated verdicts")

    artifact_paths = {
        relative(METRICS_FILE): METRICS_FILE,
        relative(DELTA_FILE): DELTA_FILE,
        relative(EVIDENCE_AUDIT_FILE): EVIDENCE_AUDIT_FILE,
        relative(PENDING_FILE): PENDING_FILE,
        relative(WORKBOOK_FILE): WORKBOOK_FILE,
    }
    manifest_artifacts = {
        row["file"]: row["sha256"] for row in manifest["output_artifacts"]
    }
    if set(manifest_artifacts) != set(artifact_paths):
        raise ValueError("M3 output artifact set mismatch")
    for file_name, path in artifact_paths.items():
        if manifest_artifacts[file_name] != sha256_file(path):
            raise ValueError(f"M3 output hash mismatch: {file_name}")

    threshold_status = manifest["threshold_status"]
    if threshold_status["decision_thresholds"]["false_accept_rate"]["passed"] is not False:
        raise ValueError("E2 FAR threshold must already be failed")
    if threshold_status["evidence_threshold"]["passed"] is not None:
        raise ValueError("Evidence threshold must remain pending before human review")
    if threshold_status["overall"] != "human_evidence_review_pending":
        raise ValueError("M3 pre-review status is invalid")

    print(
        json.dumps(
            {
                "m3_run_id": manifest["m3_run_id"],
                "evaluated_question_count": 37,
                "decision_delta_count": len(delta_rows),
                "evidence_pair_count": len(evidence_rows),
                "canonical_reuse_count": 35,
                "pending_human_review_count": len(pending_rows),
                "candidate_far": e2["false_accept_rate"],
                "candidate_far_threshold_status": "failed",
                "evidence_threshold_status": "pending",
                "validation_status": "passed",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
