"""Offline validator for the frozen A1 M3 canonical evaluation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.evaluate_evidence_review_a1 import (
    A1_MANIFEST_FILE,
    CANONICAL_DECISIONS_FILE,
    DECISION_RESULTS_FILE,
    FINAL_MANIFEST_FILE,
    FINAL_METRICS_FILE,
    INTERNAL_AUDIT_FILE,
    MANIFEST_SCHEMA_FILE,
    PRIMARY_ENTAILMENT_FILE,
    PRIMARY_REVIEWS_FILE,
    REQUEST_FILE,
    RESPONSE_SCHEMA_FILE,
    THRESHOLDS_FILE,
    build_evaluation,
    canonical_json,
    serialize_csv,
    serialize_json,
    sha256_bytes,
    sha256_file,
)
from scripts.evaluation.phase8_report_paths import (
    frozen_compatible_sha256,
    legacy_manifest_path,
)


def main() -> None:
    manifest_path = PROJECT_ROOT / FINAL_MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(manifest))
    if errors:
        raise ValueError(f"A1 M3 manifest schema failed: {errors[0].message}")

    evaluation = build_evaluation()
    expected_payloads = {
        DECISION_RESULTS_FILE.as_posix(): serialize_csv(evaluation["decision_rows"]),
        FINAL_METRICS_FILE.as_posix(): serialize_json(evaluation["metrics"]),
        INTERNAL_AUDIT_FILE.as_posix(): serialize_json(evaluation["internal_audit"]),
    }
    for relative_path, expected in expected_payloads.items():
        actual = (PROJECT_ROOT / relative_path).read_bytes()
        if actual != expected:
            raise ValueError(f"A1 M3 artifact content drift: {relative_path}")

    input_files = {
        "a1_entailment": PRIMARY_ENTAILMENT_FILE,
        "a1_manifest": A1_MANIFEST_FILE,
        "a1_reviews": PRIMARY_REVIEWS_FILE,
        "canonical_decisions": CANONICAL_DECISIONS_FILE,
        "evaluator": PROJECT_ROOT / "scripts/evaluation/evaluate_evidence_review_a1.py",
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "request_package": REQUEST_FILE,
        "response_schema": RESPONSE_SCHEMA_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    input_hashes = {
        label: frozen_compatible_sha256(path)
        for label, path in sorted(input_files.items())
    }
    if manifest["input_sha256"] != input_hashes:
        raise ValueError("A1 M3 input hash drift")
    output_hashes = {row["file"]: row["sha256"] for row in manifest["output_artifacts"]}
    expected_output_hashes = {
        legacy_manifest_path(path): sha256_bytes(content)
        for path, content in sorted(expected_payloads.items())
    }
    if output_hashes != expected_output_hashes:
        raise ValueError("A1 M3 output hash drift")
    identity = {"input_sha256": input_hashes, "output_sha256": expected_output_hashes}
    expected_run_id = "mit60001_evidence_a1_m3_" + hashlib.sha256(
        canonical_json(identity).encode("utf-8")
    ).hexdigest()[:16]
    if manifest["evaluation_run_id"] != expected_run_id:
        raise ValueError("A1 M3 evaluation identity drift")

    metrics = manifest["decision_metrics"]
    if metrics["confusion_matrix"] != {"tp": 0, "fp": 0, "fn": 21, "tn": 16}:
        raise ValueError("A1 M3 confusion matrix drift")
    evidence = manifest["evidence_selection"]
    if evidence["selected_pair_count"] != 0 or evidence["evidence_precision"] is not None:
        raise ValueError("Zero-pair evidence precision must remain undefined")
    gate = manifest["quality_gate"]
    if gate["accept_recall"]["status"] != "fail" or gate["evidence_selection_precision"]["status"] != "not_evaluable" or gate["overall_status"] != "failed_candidate":
        raise ValueError("A1 M3 frozen gate result drift")
    if manifest["model_calls"] or manifest["human_review_workbook_created"] or manifest["ground_truth_modified"] or manifest["additional_exclusions_created"]:
        raise ValueError("A1 M3 prohibited action flag drift")

    print(canonical_json({
        "evaluation_run_id": manifest["evaluation_run_id"],
        "confusion_matrix": metrics["confusion_matrix"],
        "accept_recall": metrics["accept_recall"],
        "false_accept_rate": metrics["false_accept_rate"],
        "evidence_precision_status": evidence["metric_status"],
        "selected_pair_count": evidence["selected_pair_count"],
        "overall_status": gate["overall_status"],
        "reviewer_research_status": manifest["reviewer_research_status"],
        "validation_status": "passed",
    }))


if __name__ == "__main__":
    main()
