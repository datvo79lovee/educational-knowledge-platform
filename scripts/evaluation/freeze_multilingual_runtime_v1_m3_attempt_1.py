"""Freeze Multilingual Runtime V1 - M3 attempt 1 at runtime-integrity failure.

Attempt 1 stopped at the second intent because the generator returned
``decision="abstain"`` together with a non-null answer, which the strict contract
rejects. Only 2 of 20 intents were executed, so G2-G4 have no data and no statement
about Vietnamese end-to-end quality can be made.

This script records that outcome. It does not rerun anything, does not compute quality
metrics, does not modify any attempt 1 artifact, and does not touch the runtime, the
prompts, the retriever or the pre-registration. Every attempt 1 hash is re-verified
and carried forward unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/31_multilingual_runtime_v1_m3"
PREREGISTRATION = REPORT_DIR / "m3_preregistration.json"
EXECUTION_MANIFEST = REPORT_DIR / "m3_execution_manifest.json"
RUNTIME_OUTPUTS = REPORT_DIR / "m3_runtime_outputs.jsonl"
WORKSHEET = REPORT_DIR / "m3_human_review_worksheet.csv"
METRICS_FILE = REPORT_DIR / "m3_metrics.json"
FINAL_MANIFEST = REPORT_DIR / "m3_final_manifest.json"

EXPECTED_ATTEMPT_ID = "m3-attempt-1"
EXPECTED_INTENT_COUNT = 20


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_attempt_1_unchanged(execution: dict[str, Any], prereg_hash: str) -> None:
    """Attempt 1 must be byte-identical to what the runner recorded."""

    if execution["preregistration"]["sha256"] != prereg_hash:
        raise ValueError("Pre-registration changed after attempt 1")
    if execution["execution"]["attempt_id"] != EXPECTED_ATTEMPT_ID:
        raise ValueError("Execution manifest is not attempt 1")
    if execution["quality_metrics_computed"]:
        raise ValueError("Attempt 1 must not carry computed quality metrics")
    for artifact in execution["output_artifacts"]:
        actual = sha256_file(PROJECT_ROOT / artifact["file"])
        if actual != artifact["sha256"]:
            raise ValueError(f"Attempt 1 artifact changed since execution: {artifact['file']}")
    if METRICS_FILE.exists():
        raise ValueError("m3_metrics.json exists; attempt 1 produced no evaluable metrics")
    if FINAL_MANIFEST.exists():
        raise FileExistsError("M3 final manifest already exists; attempt 1 is already frozen")


def summarise_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe what was executed without judging Vietnamese answer quality."""

    passed = [row for row in records if row["runtime_status"] == "passed"]
    failed = [row for row in records if row["runtime_status"] != "passed"]
    return {
        "executed_intent_ids": [row["intent_id"] for row in records],
        "passed_intent_ids": [row["intent_id"] for row in passed],
        "failed_intent_ids": [row["intent_id"] for row in failed],
        "failure_details": [
            {
                "intent_id": row["intent_id"],
                "error_type": row.get("error_type"),
                "error_message": row.get("error_message"),
            }
            for row in failed
        ],
    }


def main() -> None:
    prereg_hash = sha256_file(PREREGISTRATION)
    execution = json.loads(EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    verify_attempt_1_unchanged(execution, prereg_hash)

    records = load_jsonl(RUNTIME_OUTPUTS)
    counts = execution["execution"]
    if len(records) != counts["intent_count"]:
        raise ValueError("Runtime output record count differs from the execution manifest")
    if counts["retry_count"] != 0:
        raise ValueError("Attempt 1 must record zero retries")

    summary = summarise_records(records)

    manifest = {
        "schema_version": "multilingual_runtime_v1_m3_final_manifest_v1",
        "milestone": "multilingual_runtime_v1_m3",
        "status": "frozen_failed_runtime_integrity",
        "attempt_id": EXPECTED_ATTEMPT_ID,
        "preregistration": {
            "file": "reports/31_multilingual_runtime_v1_m3/m3_preregistration.json",
            "revision": execution["preregistration"]["revision"],
            "sha256": prereg_hash,
        },
        "execution_manifest": {
            "file": "reports/31_multilingual_runtime_v1_m3/m3_execution_manifest.json",
            "sha256": sha256_file(EXECUTION_MANIFEST),
            "status": execution["status"],
            "validation_status": execution["validation_status"],
        },
        "execution_counts": {
            "expected_intent_count": EXPECTED_INTENT_COUNT,
            "executed_intent_count": counts["intent_count"],
            "not_executed_intent_count": EXPECTED_INTENT_COUNT - counts["intent_count"],
            "passed_count": counts["passed_count"],
            "failed_count": counts["failed_count"],
            "translation_call_count": counts["translation_call_count"],
            "generation_call_count": counts["generation_call_count"],
            "retry_count": counts["retry_count"],
        },
        "record_summary": summary,
        "gate_results": {
            "G1": "FAIL",
            "G2": "NOT_EVALUATED",
            "G3": "NOT_EVALUATED",
            "G4": "NOT_EVALUATED",
            "overall": "FAIL",
            "gate_note": (
                "G1 failed on runtime integrity. G2-G4 were not evaluated because only 2 of 20 "
                "intents executed; they have no data and must not be reported as passed, failed "
                "or estimated."
            ),
        },
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "conclusions_not_permitted": [
            "any statement about Vietnamese end-to-end answer correctness, completeness, groundedness or citation support",
            "any decision-parity or non-inferiority comparison against the matched English baseline",
            "any Vietnamese runtime failure rate estimated from 2 executed intents",
            "any reinterpretation of the frozen M2 result",
            "any production-readiness claim",
        ],
        "observed_runtime_failure": {
            "intent_id": "mit60001-q-002",
            "error_type": "GroundedAnswerContractError",
            "contract_rule": "abstain decision requires answer=null",
            "raised_at": "src/grounded_answer/service.py strict validation of the model output",
            "classification": "generation contract violation",
            "not_evidence_of": [
                "translator failure on this intent",
                "retrieval failure on this intent",
            ],
            "novelty_note": (
                "This variant did not occur in the frozen English Reliability V1 run, which recorded "
                "40/40 public successes, 0 public failures and normalization reasons limited to "
                "abstain_literal_to_null and duplicate_supporting_ids. With 2 executed Vietnamese "
                "records this is an observation, not a rate and not a causal claim."
            ),
        },
        "diagnostic_capture_limitation": {
            "statement": (
                "The failed record does not retain the diagnostic data needed to analyse the failure. "
                "retrieval_query is null, top3_chunk_ids is empty and raw_model_output is absent, even "
                "though a translation call completed for this intent. The Pydantic error message "
                "truncates the offending model output."
            ),
            "consequence": (
                "The translation, the retrieved evidence and the full generator output for "
                "mit60001-q-002 are unrecoverable from attempt 1 artifacts."
            ),
            "scope": "Runner data capture on the error path; not a protocol violation and not a runtime defect.",
            "remedy_owner": "A future milestone with its own pre-registration; attempt 1 is not re-run to recover it.",
        },
        "attempt_integrity": {
            "artifacts_modified_by_freeze": False,
            "attempt_deleted_or_replaced": False,
            "rerun_performed": False,
            "runtime_prompt_model_or_retriever_changed": False,
            "normalization_changed": False,
        },
        "output_artifacts": [
            {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
            for path in (RUNTIME_OUTPUTS, WORKSHEET, EXECUTION_MANIFEST)
        ],
        "analysis_code_sha256_lf_normalized": {
            "scripts/evaluation/freeze_multilingual_runtime_v1_m3_attempt_1.py": sha256_file_lf(Path(__file__)),
        },
        "validation_status": "passed",
    }
    write_json(FINAL_MANIFEST, manifest)

    print(json.dumps(
        {
            "status": manifest["status"],
            "execution_counts": manifest["execution_counts"],
            "gate_results": manifest["gate_results"],
            "final_manifest_sha256": sha256_file(FINAL_MANIFEST),
        },
        indent=2, ensure_ascii=False, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
