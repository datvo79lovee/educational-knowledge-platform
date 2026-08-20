"""Validate final M3 prompt-experiment review artifacts and frozen gate result."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.phase8_report_paths import (
    frozen_compatible_sha256,
    legacy_manifest_path,
)
MANIFEST_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/m3_final_manifest.json"
SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_prompt_m3_final_manifest_v1.schema.json"
HUMAN_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/"
    "m3_human_evidence_review_canonical.csv"
)
EVIDENCE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/"
    "m3_evidence_selection_canonical.csv"
)
FINAL_METRICS_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/final_metrics.json"


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"Final M3 manifest schema failed: {errors[0].message}")

    for label, expected_hash in manifest["input_sha256"].items():
        path_by_label = {
            "canonicalizer": PROJECT_ROOT / "scripts/evaluation/canonicalize_evidence_review_prompt_experiment.py",
            "candidate_v2_e2": PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl",
            "final_manifest_schema": SCHEMA_FILE,
            "m3_pre_review_manifest": PROJECT_ROOT / "reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/m3_pre_review_manifest.json",
            "pending_human_review_package": PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_pending_evidence_review.csv",
            "pre_review_evidence_audit": PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_evidence_selection_audit.csv",
            "pre_review_metrics": PROJECT_ROOT / "reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/pre_review_decision_metrics.json",
            "review_export": PROJECT_ROOT / manifest["review_export"]["file"],
            "reviewed_workbook": PROJECT_ROOT / manifest["reviewed_workbook"]["file"],
            "thresholds": PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_thresholds.json",
        }
        if (
            label not in path_by_label
            or frozen_compatible_sha256(path_by_label[label]) != expected_hash
        ):
            raise ValueError(f"Final M3 input hash mismatch: {label}")

    output_paths = {
        legacy_manifest_path(HUMAN_FILE, PROJECT_ROOT): HUMAN_FILE,
        legacy_manifest_path(EVIDENCE_FILE, PROJECT_ROOT): EVIDENCE_FILE,
        legacy_manifest_path(FINAL_METRICS_FILE, PROJECT_ROOT): FINAL_METRICS_FILE,
    }
    manifest_outputs = {row["file"]: row["sha256"] for row in manifest["output_artifacts"]}
    if set(manifest_outputs) != set(output_paths):
        raise ValueError("Final M3 output artifact set mismatch")
    for file_name, path in output_paths.items():
        if manifest_outputs[file_name] != sha256_file(path):
            raise ValueError(f"Final M3 output hash mismatch: {file_name}")

    workbook_path = PROJECT_ROOT / manifest["reviewed_workbook"]["file"]
    export_path = PROJECT_ROOT / manifest["review_export"]["file"]
    if sha256_file(workbook_path) != manifest["reviewed_workbook"]["sha256"]:
        raise ValueError("Reviewed workbook hash mismatch")
    if sha256_file(export_path) != manifest["review_export"]["sha256"]:
        raise ValueError("Review export hash mismatch")

    human_rows = load_csv(HUMAN_FILE)
    evidence_rows = load_csv(EVIDENCE_FILE)
    if len(human_rows) != 38 or len(evidence_rows) != 73:
        raise ValueError("Expected 38 human-reviewed and 73 final evidence rows")
    human_counts = Counter(row["human_entailment_verdict"] for row in human_rows)
    if human_counts != {"supports": 22, "does_not_support": 16}:
        raise ValueError(f"Human verdict counts drift: {dict(human_counts)}")
    if any(row["human_review_status"] != "reviewed" for row in human_rows):
        raise ValueError("Human review contains an incomplete row")
    if {row["source_workbook_sha256"] for row in human_rows} != {
        manifest["reviewed_workbook"]["sha256"]
    }:
        raise ValueError("Canonical human rows do not identify the reviewed workbook")
    if any(
        row["human_entailment_verdict"] not in {"supports", "does_not_support"}
        for row in evidence_rows
    ):
        raise ValueError("Final evidence audit contains an invalid verdict")

    e2_gate_rows = [
        row
        for row in evidence_rows
        if row["candidate_e2_selected"].lower() == "true"
        and row["decision_evaluation_scope"] == "evaluated_37"
    ]
    e2_counts = Counter(row["human_entailment_verdict"] for row in e2_gate_rows)
    if len(e2_gate_rows) != 67 or e2_counts != {"supports": 46, "does_not_support": 21}:
        raise ValueError(f"E2 evidence gate counts drift: {len(e2_gate_rows)}/{dict(e2_counts)}")

    final_metrics = json.loads(FINAL_METRICS_FILE.read_text(encoding="utf-8"))
    if final_metrics != manifest["final_metrics"]:
        raise ValueError("Final metrics do not match the manifest")
    threshold_status = final_metrics["threshold_status"]
    if threshold_status["decision_thresholds"]["false_accept_rate"]["passed"] is not False:
        raise ValueError("E2 FAR threshold must fail")
    if threshold_status["evidence_threshold"]["passed"] is not False:
        raise ValueError("E2 evidence precision threshold must fail")
    if set(threshold_status["failed_thresholds"]) != {
        "false_accept_rate",
        "evidence_selection_precision",
    }:
        raise ValueError("Unexpected final failed-threshold set")
    if manifest["m3_status"] != "failed_candidate":
        raise ValueError("E2 must be frozen as a failed candidate")
    if manifest["ground_truth_modified"] or manifest["prompt_or_model_modified"]:
        raise ValueError("M3 must not modify Ground Truth, prompt or model")
    if manifest["additional_exclusions_created"]:
        raise ValueError("M3 must not create additional exclusions")

    print(json.dumps({
        "reviewed_pair_count": len(human_rows),
        "e2_gate_pair_count": len(e2_gate_rows),
        "e2_supports": e2_counts["supports"],
        "e2_does_not_support": e2_counts["does_not_support"],
        "e2_evidence_precision": final_metrics["threshold_status"]["evidence_threshold"]["value"],
        "e2_false_accept_rate": final_metrics["decision_metrics"]["candidate_v2_e2"]["false_accept_rate"],
        "m3_status": manifest["m3_status"],
        "validation_status": "passed",
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
