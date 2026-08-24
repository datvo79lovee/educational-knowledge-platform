"""Freeze Multilingual Runtime V1 M4 without rerunning the Vietnamese runtime.

M4 measured runtime failure on 20 frozen Vietnamese intents. This script verifies the
committed execution artifacts byte-for-byte, records the observed measurement and
its interpretation boundaries, and refuses to overwrite an existing final manifest.
It does not call Ollama, rerun the runtime, alter prompts or compute answer quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/32_multilingual_runtime_v1_m4"
PREREGISTRATION = REPORT_DIR / "m4_preregistration.json"
RUNTIME_OUTPUTS = REPORT_DIR / "m4_runtime_outputs.jsonl"
FAILURE_SUMMARY = REPORT_DIR / "m4_failure_summary.json"
EXECUTION_MANIFEST = REPORT_DIR / "m4_execution_manifest.json"
FINAL_MANIFEST = REPORT_DIR / "m4_final_manifest.json"

EXPECTED_ATTEMPT_ID = "m4-attempt-1"
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


def verify_execution_artifacts() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    summary = json.loads(FAILURE_SUMMARY.read_text(encoding="utf-8"))
    records = load_jsonl(RUNTIME_OUTPUTS)

    if prereg["status"] != "preregistered_not_executed" or prereg["preregistration_revision"] != 3:
        raise ValueError("M4 pre-registration is not the frozen R3 protocol")
    if execution["preregistration"]["sha256"] != sha256_file(PREREGISTRATION):
        raise ValueError("M4 pre-registration changed after execution")
    if execution["attempt_id"] != EXPECTED_ATTEMPT_ID:
        raise ValueError("Execution manifest is not M4 attempt 1")
    if execution["status"] != "executed_complete" or execution["validation_status"] != "passed":
        raise ValueError("M4 execution did not complete with valid integrity conditions")
    if execution["integrity_conditions"]["all_passed"] is not True:
        raise ValueError("M4 integrity conditions are not all PASS")
    if execution["quality_metrics_computed"] or execution["human_review_performed"]:
        raise ValueError("M4 must remain runtime-only without quality metrics or human review")

    for artifact in execution["output_artifacts"]:
        actual = sha256_file(PROJECT_ROOT / artifact["file"])
        if actual != artifact["sha256"]:
            raise ValueError(f"M4 execution artifact changed: {artifact['file']}")
    if len(records) != EXPECTED_INTENT_COUNT:
        raise ValueError("M4 runtime output does not contain all 20 records")
    counts = execution["execution"]
    if counts["retry_count"] != 0 or counts["executed_intent_count"] != EXPECTED_INTENT_COUNT:
        raise ValueError("M4 execution count or retry policy changed")
    if summary["executed_intent_count"] != EXPECTED_INTENT_COUNT:
        raise ValueError("M4 summary count does not match the frozen execution")
    return execution, summary, records


def validate_observed_measurement(records: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    passed = [row for row in records if row["runtime_status"] == "passed"]
    failed = [row for row in records if row["runtime_status"] == "failed"]
    if len(passed) != 12 or len(failed) != 8:
        raise ValueError("M4 records no longer match the observed 12 passed / 8 failed measurement")
    if any(row["failure_layer"] != "generation_contract" for row in failed):
        raise ValueError("M4 failure-layer classification changed")
    if any(row["decision"] != "answer" for row in passed):
        raise ValueError("M4 passed decision pattern changed")

    payloads = [row["raw_model_output"]["parsed"] for row in failed]
    if any(payload["decision"] != "abstain" for payload in payloads):
        raise ValueError("M4 failed payload decision pattern changed")
    answer_non_null = sum(payload["answer"] is not None for payload in payloads)
    null_answer_nonempty_support = sum(
        payload["answer"] is None and bool(payload["supporting_chunk_ids"])
        for payload in payloads
    )
    if answer_non_null != 6 or null_answer_nonempty_support != 2:
        raise ValueError("M4 abstention contract-violation variants changed")
    if summary["runtime_failure_rate"]["numerator"] != 8 or summary["runtime_failure_rate"]["denominator"] != 20:
        raise ValueError("M4 failure-rate summary changed")
    return {
        "passed_count": len(passed),
        "failed_count": len(failed),
        "all_failed_raw_decision": "abstain",
        "all_passed_response_decision": "answer",
        "abstain_with_non_null_answer_count": answer_non_null,
        "abstain_with_null_answer_and_nonempty_support_count": null_answer_nonempty_support,
    }


def build_final_manifest(
    execution: dict[str, Any], summary: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "multilingual_runtime_v1_m4_final_manifest_v1",
        "milestone": "multilingual_runtime_v1_m4",
        "status": "frozen_runtime_failure_measurement",
        "attempt_id": EXPECTED_ATTEMPT_ID,
        "preregistration": execution["preregistration"],
        "execution_manifest": {
            "file": "reports/32_multilingual_runtime_v1_m4/m4_execution_manifest.json",
            "sha256": sha256_file(EXECUTION_MANIFEST),
            "status": execution["status"],
            "validation_status": execution["validation_status"],
        },
        "observed_measurement": {
            "execution_counts": execution["execution"],
            "runtime_failure_rate": summary["runtime_failure_rate"],
            "runtime_success_rate": summary["runtime_success_rate"],
            "failure_layer_counts": summary["failure_layer_counts"],
            "failure_diagnostics_captured": {
                "raw_model_output": summary["raw_model_output_captured_on_failure"],
                "retrieval_query": summary["retrieval_query_captured_on_failure"],
                "top3": summary["top3_captured_on_failure"],
                "generation_telemetry": summary["generation_telemetry_captured_on_failure"],
            },
            "abstention_contract_patterns": observation,
        },
        "integrity_conditions": execution["integrity_conditions"],
        "runtime_sources_after_execution": execution["runtime_sources_after_execution"],
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "conclusions_not_permitted": [
            "any statement about Vietnamese answer correctness, completeness, groundedness or citation support",
            "any parity or non-inferiority comparison against the matched English baseline",
            "any causal conclusion that the Vietnamese prompt caused the observed failures",
            "treating the observed 8/20 runtime failure rate as the expected rate",
            "any production-readiness claim",
        ],
        "hypothesis_not_tested": "The Vietnamese prompt may create conflicting signals around abstention, but M4 was observational and did not test causality. No prompt or normalization change is authorized by this freeze.",
        "attempt_integrity": {
            "execution_artifacts_modified_by_freeze": False,
            "attempt_deleted_or_replaced": False,
            "rerun_performed": False,
            "runtime_prompt_model_retriever_or_normalization_changed": False,
        },
        "output_artifacts": [
            {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in (RUNTIME_OUTPUTS, FAILURE_SUMMARY, EXECUTION_MANIFEST)
        ],
        "analysis_code_sha256_lf_normalized": {
            "scripts/evaluation/freeze_multilingual_runtime_v1_m4.py": sha256_file_lf(Path(__file__))
        },
        "validation_status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Validate M4 execution artifacts without writing.")
    args = parser.parse_args()

    execution, summary, records = verify_execution_artifacts()
    observation = validate_observed_measurement(records, summary)
    if args.verify_only:
        print("verify-only: M4 execution artifacts and observed measurement are unchanged.")
        return
    if FINAL_MANIFEST.exists():
        raise FileExistsError("M4 final manifest already exists; M4 is already frozen")

    manifest = build_final_manifest(execution, summary, observation)
    write_json(FINAL_MANIFEST, manifest)
    print(json.dumps({"status": manifest["status"], "final_manifest_sha256": sha256_file(FINAL_MANIFEST)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
