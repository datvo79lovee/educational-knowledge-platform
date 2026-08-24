"""Freeze the successful M5.3 runtime-normalization attempt without rerunning it.

This script only verifies the committed pre-registration and the three execution
artifacts, then writes one final manifest. It never calls Ollama, changes runtime,
retries an intent, computes answer quality, or promotes the Vietnamese runtime to
production-ready status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3"
PREREGISTRATION = REPORT_DIR / "m5_3_preregistration.json"
RUNTIME_OUTPUTS = REPORT_DIR / "m5_3_runtime_outputs.jsonl"
GATE_RESULTS = REPORT_DIR / "m5_3_gate_results.json"
EXECUTION_MANIFEST = REPORT_DIR / "m5_3_execution_manifest.json"
FINAL_MANIFEST = REPORT_DIR / "m5_3_final_manifest.json"

EXPECTED_ATTEMPT_ID = "m5-3-attempt-1"
EXPECTED_INTENT_COUNT = 20
EXPECTED_NORMALIZATION_COUNT = 8
NEW_NORMALIZATION_REASON = "vi_abstain_payload_to_canonical"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_execution_artifacts() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    prereg = load_json(PREREGISTRATION)
    execution = load_json(EXECUTION_MANIFEST)
    gate_results = load_json(GATE_RESULTS)
    records = load_jsonl(RUNTIME_OUTPUTS)

    if prereg["status"] != "preregistered_not_executed" or prereg["preregistration_revision"] != 3:
        raise ValueError("M5.3 pre-registration is not the committed revision 3 protocol")
    if execution["preregistration"]["sha256"] != sha256_file(PREREGISTRATION):
        raise ValueError("M5.3 pre-registration changed after execution")
    if execution["attempt_id"] != EXPECTED_ATTEMPT_ID:
        raise ValueError("Execution manifest is not M5.3 attempt 1")
    if execution["status"] != "executed_complete" or execution["validation_status"] != "passed":
        raise ValueError("M5.3 execution is not the completed passing attempt")
    if execution["quality_metrics_computed"] or execution["human_review_performed"]:
        raise ValueError("M5.3 must remain runtime-only without quality metrics or human review")
    if execution["runtime_sources_after_execution"]["result"] != "PASS":
        raise ValueError("M5.3 runtime source integrity did not pass after execution")

    for artifact in execution["output_artifacts"]:
        if sha256_file(PROJECT_ROOT / artifact["file"]) != artifact["sha256"]:
            raise ValueError(f"M5.3 execution artifact changed: {artifact['file']}")
    if gate_results["gates"] != execution["gates"]:
        raise ValueError("M5.3 gate results differ from the execution manifest")
    return execution, gate_results, records


def validate_passing_attempt(
    execution: dict[str, Any], gate_results: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    gates = execution["gates"]
    expected_gate_results = {
        "G1_execution_integrity": "PASS",
        "G2_runtime_failure": "PASS",
        "G3_scope_integrity": "PASS",
        "G4_normalization_integrity": "PASS",
    }
    observed_gate_results = {
        name: gates["conditions"][name]["result"] for name in expected_gate_results
    }
    if gates["all_passed"] is not True or observed_gate_results != expected_gate_results:
        raise ValueError(f"M5.3 gate pattern changed: {observed_gate_results}")

    counts = execution["execution"]
    if (
        counts["executed_intent_count"] != EXPECTED_INTENT_COUNT
        or counts["passed_count"] != EXPECTED_INTENT_COUNT
        or counts["total_runtime_failure_count"] != 0
        or counts["retry_count"] != 0
    ):
        raise ValueError("M5.3 execution counts or retry policy changed")
    if any(counts[name] != EXPECTED_INTENT_COUNT for name in (
        "translation_call_count", "retrieval_call_count", "generation_call_count"
    )):
        raise ValueError("M5.3 stage call counts changed")
    if len(records) != EXPECTED_INTENT_COUNT or len({row["intent_id"] for row in records}) != EXPECTED_INTENT_COUNT:
        raise ValueError("M5.3 records are not exactly the frozen 20 intents")
    if any(row["runtime_status"] != "passed" for row in records):
        raise ValueError("M5.3 contains a runtime failure despite the passing manifest")
    if any(
        row[field] != 1
        for row in records
        for field in ("translation_call_count", "retrieval_call_count", "generation_call_count")
    ):
        raise ValueError("M5.3 contains a record without exactly one call per stage")

    normalized = [
        row for row in records
        if row["normalization_reason"] == NEW_NORMALIZATION_REASON
    ]
    if len(normalized) != EXPECTED_NORMALIZATION_COUNT:
        raise ValueError("M5.3 observed normalization count changed")
    for row in normalized:
        raw = row["raw_model_output"]["parsed"]
        if (
            raw["decision"] != "abstain"
            or row["normalization_applied"] is not True
            or row["decision"] != "abstain"
            or row["answer"] is not None
            or row["supporting_chunk_ids"]
            or row["citations"]
            or row["normalized_output"]["decision"] != "abstain"
            or row["normalized_output"]["answer"] is not None
            or row["normalized_output"]["supporting_chunk_ids"] != []
        ):
            raise ValueError(f"M5.3 normalized record changed shape: {row['intent_id']}")
        if not set(raw["supporting_chunk_ids"]).issubset(set(row["top3_chunk_ids"])):
            raise ValueError(f"M5.3 normalized record has an out-of-Top-3 raw ID: {row['intent_id']}")
    return {
        "executed_intent_count": counts["executed_intent_count"],
        "passed_count": counts["passed_count"],
        "total_runtime_failure_count": counts["total_runtime_failure_count"],
        "normalization_reason": NEW_NORMALIZATION_REASON,
        "normalized_record_count": len(normalized),
        "normalized_intent_ids": [row["intent_id"] for row in normalized],
    }


def build_final_manifest(
    execution: dict[str, Any], gate_results: dict[str, Any], observed: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "multilingual_runtime_v1_m5_3_final_manifest_v1",
        "milestone": "multilingual_runtime_v1_m5",
        "stage": "m5.3",
        "status": "frozen_passed_runtime_gates",
        "attempt_id": EXPECTED_ATTEMPT_ID,
        "candidate_decision": "ADVANCE_TO_M6_QUALITY_EVALUATION",
        "preregistration": execution["preregistration"],
        "execution_manifest": {
            "file": "reports/34_multilingual_runtime_v1_m5_3/m5_3_execution_manifest.json",
            "sha256": sha256_file(EXECUTION_MANIFEST),
            "status": execution["status"],
            "validation_status": execution["validation_status"],
        },
        "gate_results": execution["gates"],
        "observed_execution": {
            **execution["execution"],
            "runtime_failure_rate": gate_results["summary"]["runtime_failure_rate"],
            "failure_layer_counts": gate_results["summary"]["failure_layer_counts"],
            "normalization": observed,
        },
        "scope_integrity_before_execution": execution["scope_integrity_before_execution"],
        "scope_integrity_after_execution": execution["scope_integrity_after_execution"],
        "runtime_sources_after_execution": execution["runtime_sources_after_execution"],
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "runtime_integrity_interpretation": (
            "M5.3 shows that this registered application-boundary normalization completed "
            "the frozen 20-intent runtime attempt without a contract failure. It is not an "
            "answer-quality, groundedness, citation-support, translation-fidelity, English-parity "
            "or production-readiness result."
        ),
        "conclusions_not_permitted": [
            "Vietnamese answer correctness, completeness, groundedness or citation support",
            "translation semantic fidelity or retrieval quality",
            "parity or non-inferiority against English",
            "production readiness or demo readiness",
            "causal proof that the normalization caused improvement over M4 or M5.1",
            "treating the observed zero failures as an expected runtime failure rate",
        ],
        "next_step_requires_preregistration": "M6 human evaluation of Vietnamese end-to-end answer quality",
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
            "scripts/evaluation/freeze_multilingual_runtime_v1_m5_3.py": sha256_file_lf(Path(__file__))
        },
        "validation_status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Validate M5.3 execution artifacts without writing.")
    args = parser.parse_args()

    execution, gate_results, records = verify_execution_artifacts()
    observed = validate_passing_attempt(execution, gate_results, records)
    if args.verify_only:
        print("verify-only: M5.3 passing attempt and gate results are unchanged.")
        return
    if FINAL_MANIFEST.exists():
        raise FileExistsError("M5.3 final manifest already exists; M5.3 is already frozen")

    manifest = build_final_manifest(execution, gate_results, observed)
    write_json(FINAL_MANIFEST, manifest)
    print(json.dumps({
        "status": manifest["status"],
        "candidate_decision": manifest["candidate_decision"],
        "final_manifest_sha256": sha256_file(FINAL_MANIFEST),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
