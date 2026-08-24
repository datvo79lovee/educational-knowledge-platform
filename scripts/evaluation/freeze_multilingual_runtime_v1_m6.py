"""Freeze the M6 human quality evaluation of the frozen M5.3 candidate.

This script only verifies the six M6-E artifacts and writes one final manifest. It
never calls Ollama, reruns ``--evaluate``, translation or retrieval, and never touches
a reviewed label, a result artifact, M5.3, the runtime, the prompt, normalization, or
Dense/index/Gold/Ground Truth. It is re-runnable and read-only with respect to the
runtime: running it twice against the same artifacts produces the same manifest and
raises before writing a second time.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/35_multilingual_runtime_v1_m6"
PREREGISTRATION = REPORT_DIR / "m6_preregistration.json"
PREPARATION_MANIFEST = REPORT_DIR / "m6_preparation_manifest.json"
REVIEWED_WORKSHEET = REPORT_DIR / "m6_human_review_worksheet_reviewed.csv"
FINAL_RESULTS = REPORT_DIR / "m6_final_results.csv"
METRICS = REPORT_DIR / "m6_metrics.json"
EVALUATION_MANIFEST = REPORT_DIR / "m6_evaluation_manifest.json"
FINAL_MANIFEST = REPORT_DIR / "m6_final_manifest.json"

EXPECTED_STATUS = "evaluated_passed"
EXPECTED_PRIMARY_COUNT = 19
EXPECTED_EXCLUDED_COUNT = 1
REQUIRED_GATE_IDS = (
    "G1_review_integrity",
    "G2_language_compliance",
    "G3_decision_non_inferiority",
    "G4_strict_end_to_end_non_inferiority",
)

ALLOWED_CONCLUSION = (
    "The frozen M5.3 Vietnamese candidate passed M6 quality gates on the 19-record "
    "primary reused evaluation sample."
)
FORBIDDEN_CONCLUSIONS = (
    "production-ready",
    "generalizes to unseen queries",
    "causal attribution of any failure to translation, retrieval, or generation",
    "translator fidelity restored",
    "M2 failure reversed or overturned",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_m6_e_unchanged(evaluation: dict[str, Any]) -> dict[str, str]:
    """Re-hash the six M6-E artifacts and confirm they match what evaluate() recorded.

    This is the only correctness check that matters for a freeze script: the artifacts
    it is about to describe must be byte-identical to the ones ``--evaluate`` produced,
    not merely present.
    """

    observed = {
        "preregistration": sha256_file(PREREGISTRATION),
        "preparation_manifest": sha256_file(PREPARATION_MANIFEST),
        "reviewed_worksheet": sha256_file(REVIEWED_WORKSHEET),
        "final_results": sha256_file(FINAL_RESULTS),
        "metrics": sha256_file(METRICS),
        "evaluation_manifest": sha256_file(EVALUATION_MANIFEST),
    }

    if observed["preregistration"] != evaluation["preregistration_sha256"]:
        raise ValueError("Pre-registration changed after M6-E evaluation")
    if observed["preparation_manifest"] != evaluation["preparation_manifest_sha256"]:
        raise ValueError("Preparation manifest changed after M6-E evaluation")
    if observed["reviewed_worksheet"] != evaluation["reviewed_worksheet_sha256"]:
        raise ValueError("Reviewed worksheet changed after M6-E evaluation")

    recorded_outputs = {item["file"]: item["sha256"] for item in evaluation["output_artifacts"]}
    final_results_key = str(FINAL_RESULTS.relative_to(PROJECT_ROOT)).replace("\\", "/")
    metrics_key = str(METRICS.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if observed["final_results"] != recorded_outputs.get(final_results_key):
        raise ValueError("Final results CSV changed after M6-E evaluation")
    if observed["metrics"] != recorded_outputs.get(metrics_key):
        raise ValueError("Metrics JSON changed after M6-E evaluation")

    return observed


def verify_gates(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Re-derive PASS/FAIL from the evaluation manifest; never recompute a metric."""

    gates = evaluation["gates"]
    if not gates["all_passed"]:
        raise ValueError("M6-E did not pass; freeze must not proceed on a failed evaluation")
    conditions = gates["conditions"]
    missing = [gate_id for gate_id in REQUIRED_GATE_IDS if gate_id not in conditions]
    if missing:
        raise ValueError(f"Evaluation manifest is missing required gates: {missing}")
    not_passed = [
        gate_id for gate_id in REQUIRED_GATE_IDS if conditions[gate_id].get("result") != "PASS"
    ]
    if not_passed:
        raise ValueError(f"Gate(s) not PASS in evaluation manifest: {not_passed}")
    return {gate_id: conditions[gate_id] for gate_id in REQUIRED_GATE_IDS}


def verify_scope(evaluation: dict[str, Any], metrics: dict[str, Any]) -> None:
    if evaluation["status"] != EXPECTED_STATUS:
        raise ValueError(f"Evaluation manifest status is not {EXPECTED_STATUS}: {evaluation['status']}")
    if evaluation["runtime_calls"] != 0:
        raise ValueError("M6-E recorded a nonzero runtime call count")
    if evaluation["ground_truth_modified"] is not False:
        raise ValueError("M6-E recorded a Ground Truth modification")
    if not evaluation["quality_metrics_computed"]:
        raise ValueError("M6-E did not record quality metrics as computed")
    if metrics["primary_count"] != EXPECTED_PRIMARY_COUNT:
        raise ValueError(f"Primary count is not {EXPECTED_PRIMARY_COUNT}: {metrics['primary_count']}")
    if len(metrics["excluded_intent_ids"]) != EXPECTED_EXCLUDED_COUNT:
        raise ValueError("Excluded intent count differs from the pre-registered scope")


def ensure_not_already_frozen() -> None:
    if FINAL_MANIFEST.exists():
        raise FileExistsError(
            "M6 final manifest already exists; this milestone is already frozen. "
            "Rerun requires deleting the manifest deliberately, which this script never does."
        )


def main() -> None:
    ensure_not_already_frozen()

    evaluation = load_json(EVALUATION_MANIFEST)
    metrics_file = load_json(METRICS)
    metrics = metrics_file["metrics"]
    artifact_hashes = verify_m6_e_unchanged(evaluation)
    gate_snapshot = verify_gates(evaluation)
    verify_scope(evaluation, metrics)

    manifest = {
        "schema_version": "multilingual_runtime_v1_m6_final_manifest_v1",
        "milestone": "multilingual_runtime_v1_m6",
        "status": "frozen_passed_quality_gates",
        "m6_e_artifacts_sha256": artifact_hashes,
        "gates": {
            "all_passed": True,
            "pass_rule": "G1, G2, G3 and G4 must all PASS",
            "conditions": gate_snapshot,
        },
        "primary_count": metrics["primary_count"],
        "excluded_intent_ids": metrics["excluded_intent_ids"],
        "decision_correct": metrics["decision_correct"],
        "language_compliance": metrics["language_compliance"],
        "strict_end_to_end_success": metrics["strict_end_to_end_success"],
        "strict_answer_success_diagnostic": metrics["strict_answer_success_diagnostic"],
        "matched_english_reference": metrics["matched_english_reference"],
        "runtime_calls": 0,
        "ground_truth_modified": False,
        "rerun_performed": False,
        "evaluator_output_mutated": False,
        "reviewed_labels_mutated": False,
        "runtime_prompt_normalization_dense_index_gold_or_ground_truth_changed": False,
        "allowed_conclusion": ALLOWED_CONCLUSION,
        "forbidden_conclusions": FORBIDDEN_CONCLUSIONS,
        "interpretation_boundary": {
            "m5_3_result": "PASS for frozen runtime-integrity and normalization gates only",
            "m6_result": "PASS for human quality gates on the reused 19-record primary sample",
            "production_readiness_claim_allowed": False,
            "unseen_query_generalization_claim_allowed": False,
            "causal_attribution_claim_allowed": False,
            "translator_fidelity_restored_claim_allowed": False,
            "m2_failure_reversed_claim_allowed": False,
            "pass_interpretation": (
                "A PASS may advance the unchanged candidate to a separately scoped bounded "
                "local-demo milestone. It does not establish production readiness or "
                "unseen-query generalization, and it does not reopen or reverse the frozen M2 "
                "literal-translator rejection."
            ),
            "fixed_sample_limitation": (
                "These 20 intents have been reused throughout multilingual development. M6 "
                "measures this frozen development/evaluation sample, not an unseen test set."
            ),
            "single_reviewer_limitation": (
                "M6 is one review pass by one reviewer. It measures neither inter-annotator "
                "agreement nor delayed intra-annotator consistency."
            ),
        },
        "output_artifacts": [
            {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": artifact_hashes[key]}
            for path, key in (
                (PREREGISTRATION, "preregistration"),
                (PREPARATION_MANIFEST, "preparation_manifest"),
                (REVIEWED_WORKSHEET, "reviewed_worksheet"),
                (FINAL_RESULTS, "final_results"),
                (METRICS, "metrics"),
                (EVALUATION_MANIFEST, "evaluation_manifest"),
            )
        ],
        "validation_status": "passed",
    }
    write_json(FINAL_MANIFEST, manifest)

    print(f"M6 frozen: {FINAL_MANIFEST.relative_to(PROJECT_ROOT)}")
    print(f"status: {manifest['status']}")
    print(f"gates all_passed: {manifest['gates']['all_passed']}")


if __name__ == "__main__":
    main()
