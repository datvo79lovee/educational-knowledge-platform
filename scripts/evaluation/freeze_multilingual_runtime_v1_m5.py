"""Freeze the failed M5.1 prompt-candidate attempt without rerunning runtime.

The script verifies the pre-registration, execution outputs and failed gate result
byte-for-byte, records the observed q-025 contract violation, and refuses to overwrite
an existing final manifest. It does not call Ollama, alter the prompt, retry the
attempt, compute answer quality or open another candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/33_multilingual_runtime_v1_m5"
PREREGISTRATION = REPORT_DIR / "m5_preregistration.json"
RUNTIME_OUTPUTS = REPORT_DIR / "m5_1_runtime_outputs.jsonl"
GATE_RESULTS = REPORT_DIR / "m5_1_gate_results.json"
EXECUTION_MANIFEST = REPORT_DIR / "m5_1_execution_manifest.json"
FINAL_MANIFEST = REPORT_DIR / "m5_1_final_manifest.json"

EXPECTED_ATTEMPT_ID = "m5-1-attempt-1"
EXPECTED_FAILED_INTENT = "mit60001-q-025"
EXPECTED_INTENT_COUNT = 20


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_execution_artifacts() -> tuple[
    dict[str, Any], dict[str, Any], list[dict[str, Any]]
]:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    gate_results = json.loads(GATE_RESULTS.read_text(encoding="utf-8"))
    records = load_jsonl(RUNTIME_OUTPUTS)

    if prereg["status"] != "preregistered_not_executed" or prereg["preregistration_revision"] != 5:
        raise ValueError("M5.1 pre-registration is not the frozen revision 5 protocol")
    if execution["preregistration"]["sha256"] != sha256_file(PREREGISTRATION):
        raise ValueError("M5.1 pre-registration changed after execution")
    if execution["attempt_id"] != EXPECTED_ATTEMPT_ID:
        raise ValueError("Execution manifest is not M5.1 attempt 1")
    if execution["status"] != "executed_complete" or execution["validation_status"] != "failed_gates":
        raise ValueError("M5.1 execution status no longer matches the failed completed attempt")
    if execution["quality_metrics_computed"] or execution["human_review_performed"]:
        raise ValueError("M5.1 must remain runtime-only without quality metrics or human review")
    if execution["runtime_sources_after_execution"]["result"] != "PASS":
        raise ValueError("M5.1 runtime source integrity did not pass after execution")

    for artifact in execution["output_artifacts"]:
        actual = sha256_file(PROJECT_ROOT / artifact["file"])
        if actual != artifact["sha256"]:
            raise ValueError(f"M5.1 execution artifact changed: {artifact['file']}")
    if gate_results["gates"] != execution["gates"]:
        raise ValueError("M5.1 gate results differ from the execution manifest")
    if len(records) != EXPECTED_INTENT_COUNT:
        raise ValueError("M5.1 runtime output no longer contains exactly 20 records")

    counts = execution["execution"]
    if (
        counts["executed_intent_count"] != EXPECTED_INTENT_COUNT
        or counts["passed_count"] != 19
        or counts["total_runtime_failure_count"] != 1
        or counts["retry_count"] != 0
    ):
        raise ValueError("M5.1 execution counts or retry policy changed")
    if any(counts[name] != EXPECTED_INTENT_COUNT for name in (
        "translation_call_count", "retrieval_call_count", "generation_call_count"
    )):
        raise ValueError("M5.1 stage call counts changed")
    return execution, gate_results, records


def validate_failed_gate(
    execution: dict[str, Any], gate_results: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    gates = execution["gates"]
    conditions = gates["conditions"]
    if gates["all_passed"] is not False:
        raise ValueError("M5.1 overall gate result is no longer FAIL")
    expected = {
        "G1_execution_integrity": "PASS",
        "G2_runtime_failure": "FAIL",
        "G3_scope_integrity": "PASS",
    }
    observed = {name: conditions[name]["result"] for name in expected}
    if observed != expected:
        raise ValueError(f"M5.1 gate pattern changed: {observed}")
    if conditions["G2_runtime_failure"]["total_runtime_failure_count"] != 1:
        raise ValueError("M5.1 G2 failure count changed")
    if conditions["G2_runtime_failure"]["generation_contract_failure_count"] != 1:
        raise ValueError("M5.1 generation-contract count changed")

    failed = [row for row in records if row["runtime_status"] == "failed"]
    if len(failed) != 1 or failed[0]["intent_id"] != EXPECTED_FAILED_INTENT:
        raise ValueError("M5.1 failed intent changed")
    record = failed[0]
    if record["failure_layer"] != "generation_contract" or record["error_type"] != "GroundedAnswerContractError":
        raise ValueError("M5.1 failure classification changed")
    payload = record["raw_model_output"]["parsed"]
    if not (
        payload["decision"] == "abstain"
        and payload["answer"] is None
        and len(payload["supporting_chunk_ids"]) == 1
    ):
        raise ValueError("M5.1 q-025 abstention violation changed")
    if gate_results["summary"]["failed_intent_ids"] != [EXPECTED_FAILED_INTENT]:
        raise ValueError("M5.1 summary failed-intent list changed")
    return {
        "intent_id": record["intent_id"],
        "failure_layer": record["failure_layer"],
        "error_type": record["error_type"],
        "raw_decision": payload["decision"],
        "raw_answer": payload["answer"],
        "raw_supporting_chunk_ids": payload["supporting_chunk_ids"],
        "diagnostics_captured": {
            "raw_model_output": record["raw_model_output"] is not None,
            "retrieval_query": bool(record["retrieval_query"]),
            "top3_chunk_ids": len(record["top3_chunk_ids"]) == 3,
            "generation_telemetry": record["generation_eval_count"] is not None,
        },
    }


def build_final_manifest(
    execution: dict[str, Any], gate_results: dict[str, Any], failure: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "multilingual_runtime_v1_m5_1_final_manifest_v1",
        "milestone": "multilingual_runtime_v1_m5",
        "stage": "m5.1",
        "status": "frozen_failed_runtime_gate",
        "attempt_id": EXPECTED_ATTEMPT_ID,
        "candidate_decision": "REJECTED",
        "preregistration": execution["preregistration"],
        "execution_manifest": {
            "file": "reports/33_multilingual_runtime_v1_m5/m5_1_execution_manifest.json",
            "sha256": sha256_file(EXECUTION_MANIFEST),
            "status": execution["status"],
            "validation_status": execution["validation_status"],
        },
        "gate_results": execution["gates"],
        "observed_execution": {
            **execution["execution"],
            "runtime_failure_rate": gate_results["summary"]["runtime_failure_rate"],
            "failure_layer_counts": gate_results["summary"]["failure_layer_counts"],
            "failed_record": failure,
        },
        "prompt_identity": execution["prompt_identity"],
        "scope_integrity_before_execution": execution["scope_integrity_before_execution"],
        "scope_integrity_after_execution": execution["scope_integrity_after_execution"],
        "runtime_sources_after_execution": execution["runtime_sources_after_execution"],
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "rollback_required_by_preregistration": True,
        "rollback_performed_by_freeze": False,
        "new_candidate_opened": False,
        "conclusions_not_permitted": [
            "Vietnamese answer quality, groundedness or citation support",
            "parity or non-inferiority against English",
            "production readiness",
            "causal proof that the previous prompt caused M4 failures",
            "causal proof that the M5 prompt reduced failures",
            "treating the observed 1/20 rate as an expected runtime failure rate",
        ],
        "comparison_boundary": (
            "M4 observed 8/20 failures and M5.1 observed 1/20, but the translator and "
            "generation process are not guaranteed deterministic. This descriptive difference "
            "is not a causal or systematic-improvement claim."
        ),
        "attempt_integrity": {
            "execution_artifacts_modified_by_freeze": False,
            "attempt_deleted_or_replaced": False,
            "rerun_performed": False,
            "runtime_prompt_model_retriever_or_normalization_changed_by_freeze": False,
        },
        "output_artifacts": [
            {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in (RUNTIME_OUTPUTS, GATE_RESULTS, EXECUTION_MANIFEST)
        ],
        "analysis_code_sha256_lf_normalized": {
            "scripts/evaluation/freeze_multilingual_runtime_v1_m5.py": sha256_file_lf(Path(__file__))
        },
        "validation_status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Validate M5.1 artifacts without writing.")
    args = parser.parse_args()

    execution, gate_results, records = verify_execution_artifacts()
    failure = validate_failed_gate(execution, gate_results, records)
    if args.verify_only:
        print("verify-only: M5.1 failed attempt and gate results are unchanged.")
        return
    if FINAL_MANIFEST.exists():
        raise FileExistsError("M5.1 final manifest already exists; M5.1 is already frozen")

    manifest = build_final_manifest(execution, gate_results, failure)
    write_json(FINAL_MANIFEST, manifest)
    print(json.dumps({
        "status": manifest["status"],
        "candidate_decision": manifest["candidate_decision"],
        "final_manifest_sha256": sha256_file(FINAL_MANIFEST),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
