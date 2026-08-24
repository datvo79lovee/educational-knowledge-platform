"""M5.3: measure one Vietnamese-only fail-closed abstention normalization candidate.

The candidate changes only ``normalize_model_output`` and its service call site. Raw
model output remains captured; the application may canonicalize a Vietnamese abstain
decision to ``answer=null`` and no supporting IDs only when every supplied ID belongs
to the request's Dense Top 3. English behavior and the strict contracts remain frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.run_multilingual_runtime_v1_m3 import wilson_interval  # noqa: E402
from scripts.evaluation.run_multilingual_runtime_v1_m4 import (  # noqa: E402
    FAILURE_LAYERS,
    RecordingGenerationProvider,
    RecordingSearchService,
    RecordingTranslator,
    classify_failure,
    extract_raw_model_output,
    raw_output_from_recorder,
    sha256_file,
    sha256_file_lf,
    stage_telemetry,
    write_jsonl_atomic,
)
from scripts.evaluation.run_multilingual_runtime_v1_m5 import diagnostic_gaps  # noqa: E402
from src.grounded_answer.prompts import (  # noqa: E402
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    VI_PROMPT_VERSION,
    VI_SYSTEM_PROMPT,
    build_user_prompt,
)
from src.grounded_answer.service import (  # noqa: E402
    MODEL_DIGEST,
    GroundedAnswerService,
    build_default_provider,
    normalize_model_output,
)
from src.multilingual.translation import build_default_translation_provider  # noqa: E402
from src.search_api.service import DenseSearchService  # noqa: E402


REPORT_DIR = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3"
PREREGISTRATION = REPORT_DIR / "m5_3_preregistration.json"
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
RUNTIME_OUTPUTS = REPORT_DIR / "m5_3_runtime_outputs.jsonl"
GATE_RESULTS = REPORT_DIR / "m5_3_gate_results.json"
EXECUTION_MANIFEST = REPORT_DIR / "m5_3_execution_manifest.json"
RESULT_ARTIFACT_NAMES = (
    "m5_3_runtime_outputs.jsonl",
    "m5_3_gate_results.json",
    "m5_3_execution_manifest.json",
)

ATTEMPT_ID = "m5-3-attempt-1"
EXPECTED_INTENT_COUNT = 20
ANSWER_LANGUAGE = "vi"
NEW_NORMALIZATION_REASON = "vi_abstain_payload_to_canonical"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_sha(value: Any) -> str:
    return sha256_text(inspect.getsource(value).replace("\r\n", "\n"))


def verify_hash_map(expected_map: dict[str, str], *, lf: bool, label: str) -> None:
    if not expected_map:
        raise ValueError(f"Pre-registration does not pin any {label}")
    mismatches = []
    for relative_path, expected in expected_map.items():
        path = PROJECT_ROOT / relative_path
        actual = sha256_file_lf(path) if lf else sha256_file(path)
        if actual != expected:
            mismatches.append(relative_path)
    if mismatches:
        raise ValueError(f"{label} changed since pre-registration: " + ", ".join(mismatches))


def verify_frozen_inputs(prereg: dict[str, Any]) -> None:
    verify_hash_map(prereg["frozen_inputs_sha256"], lf=False, label="Frozen input")


def runtime_source_mismatches(prereg: dict[str, Any]) -> list[str]:
    expected = prereg["runtime_under_test"]["source_sha256_lf_normalized"]
    return [
        path for path, digest in expected.items()
        if sha256_file_lf(PROJECT_ROOT / path) != digest
    ]


def verify_runtime_sources(prereg: dict[str, Any]) -> None:
    mismatches = runtime_source_mismatches(prereg)
    if mismatches:
        raise ValueError("Runtime under test changed since pre-registration: " + ", ".join(mismatches))


def analysis_code_mismatches(prereg: dict[str, Any]) -> list[str]:
    expected = prereg["analysis_code_sha256_lf_normalized"]
    return [
        path for path, digest in expected.items()
        if sha256_file_lf(PROJECT_ROOT / path) != digest
    ]


def verify_analysis_code(prereg: dict[str, Any]) -> None:
    mismatches = analysis_code_mismatches(prereg)
    if mismatches:
        raise ValueError("Analysis code changed since pre-registration: " + ", ".join(mismatches))


def runtime_symbol_report(prereg: dict[str, Any]) -> dict[str, Any]:
    pins = prereg["scope_integrity"]["runtime_symbols"]
    observed: dict[str, str] = {
        "normalize_model_output_source_sha256": source_sha(normalize_model_output),
        "grounded_answer_service_answer_source_sha256": source_sha(GroundedAnswerService.answer),
        "build_default_provider_source_sha256": source_sha(build_default_provider),
        "model_digest": MODEL_DIGEST,
        "system_prompt_sha256": sha256_text(SYSTEM_PROMPT),
        "vi_system_prompt_sha256": sha256_text(VI_SYSTEM_PROMPT),
        "prompt_version": PROMPT_VERSION,
        "vi_prompt_version": VI_PROMPT_VERSION,
        "build_user_prompt_source_sha256": source_sha(build_user_prompt),
    }
    candidate = {
        "normalize_model_output_source_sha256",
        "grounded_answer_service_answer_source_sha256",
    }
    entries = {
        name: {
            "role": "authorized_candidate" if name in candidate else "frozen",
            "expected": pins[name],
            "observed": value,
            "result": "PASS" if value == pins[name] else "FAIL",
        }
        for name, value in observed.items()
    }
    mismatches = sorted(name for name, entry in entries.items() if entry["result"] == "FAIL")
    return {"symbols": entries, "mismatched_symbols": mismatches, "result": "PASS" if not mismatches else "FAIL"}


def scope_integrity_report(prereg: dict[str, Any]) -> dict[str, Any]:
    scope = prereg["scope_integrity"]
    baseline = scope["baseline_runtime_sources_sha256_lf_normalized"]
    authorized = sorted(scope["authorized_changed_files"])
    changed = sorted(
        path for path, digest in baseline.items()
        if sha256_file_lf(PROJECT_ROOT / path) != digest
    )
    unauthorized = sorted(set(changed) - set(authorized))
    missing = sorted(set(authorized) - set(changed))
    symbols = runtime_symbol_report(prereg)
    passed = not unauthorized and not missing and changed == authorized and symbols["result"] == "PASS"
    return {
        "baseline_milestone": "multilingual_runtime_v1_m5_2",
        "authorized_changed_files": authorized,
        "observed_changed_files": changed,
        "unauthorized_changed_files": unauthorized,
        "authorized_files_without_change": missing,
        "runtime_symbols": symbols,
        "result": "PASS" if passed else "FAIL",
    }


def ensure_no_existing_result_artifacts() -> None:
    existing = [name for name in RESULT_ARTIFACT_NAMES if (REPORT_DIR / name).exists()]
    if existing:
        raise FileExistsError("M5.3 result artifacts already exist: " + ", ".join(existing))


def execute_intent(
    service: GroundedAnswerService,
    translator: RecordingTranslator,
    search: RecordingSearchService,
    generator: RecordingGenerationProvider,
    intent: dict[str, Any],
) -> dict[str, Any]:
    translator.reset()
    search.reset()
    generator.reset()
    started = time.perf_counter()
    record: dict[str, Any] = {
        "schema_version": "multilingual_runtime_v1_m5_3_output_v1",
        "execution_attempt_id": ATTEMPT_ID,
        "intent_id": intent["intent_id"],
        "original_query": intent["question_vi"],
        "answer_language": ANSWER_LANGUAGE,
    }
    try:
        execution = service.answer(intent["question_vi"], ANSWER_LANGUAGE)
    except Exception as error:  # noqa: BLE001 - failures are evaluation data
        record.update(stage_telemetry(translator, search, generator))
        record.update({
            "runtime_status": "failed",
            "failure_layer": classify_failure(error),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
            "raw_model_output": raw_output_from_recorder(generator) or extract_raw_model_output(error),
            "normalized_output": None,
            "decision": None,
            "answer": None,
            "supporting_chunk_ids": [],
            "citations": [],
            "normalization_applied": None,
            "normalization_reason": None,
            "index_run_id": None,
            "total_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        })
        return record

    response = execution.response
    record.update(stage_telemetry(translator, search, generator))
    record.update({
        "runtime_status": "passed",
        "failure_layer": None,
        "error_type": None,
        "error_message": None,
        "cause_type": None,
        "raw_model_output": raw_output_from_recorder(generator),
        "normalized_output": execution.normalized_output,
        "decision": response.decision,
        "answer": response.answer,
        "supporting_chunk_ids": list(response.supporting_chunk_ids),
        "citations": [citation.model_dump() for citation in response.citations],
        "normalization_applied": execution.normalization_applied,
        "normalization_reason": execution.normalization_reason,
        "index_run_id": execution.index_run_id,
        "total_latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
    })
    return record


def run_execution(
    service: GroundedAnswerService,
    translator: RecordingTranslator,
    search: RecordingSearchService,
    generator: RecordingGenerationProvider,
    intents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for intent in intents:
        record = execute_intent(service, translator, search, generator, intent)
        records.append(record)
        write_jsonl_atomic(RUNTIME_OUTPUTS, records)
        print(
            f"  {record['intent_id']} {record['runtime_status']:7} "
            f"{(record['decision'] or '-'):8} {(record['normalization_reason'] or '-'):34} "
            f"{record['total_latency_ms']:9.1f}ms"
        )
    return records


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [row for row in records if row["runtime_status"] != "passed"]
    passed = [row for row in records if row["runtime_status"] == "passed"]
    total = len(records)
    low, high = wilson_interval(len(failed), total) if total else (None, None)
    return {
        "schema_version": "multilingual_runtime_v1_m5_3_summary_v1",
        "attempt_id": ATTEMPT_ID,
        "executed_intent_count": total,
        "passed_count": len(passed),
        "total_runtime_failure_count": len(failed),
        "runtime_failure_rate": {
            "numerator": len(failed), "denominator": total,
            "rate": round(len(failed) / total, 9) if total else None,
            "wilson_95": [low, high],
        },
        "failure_layer_counts": {
            layer: sum(row["failure_layer"] == layer for row in failed) for layer in FAILURE_LAYERS
        },
        "failed_intent_ids": [row["intent_id"] for row in failed],
        "decision_counts_among_passed": {
            value: sum(row["decision"] == value for row in passed) for value in ("answer", "abstain")
        },
        "normalization_reason_counts": {
            reason: sum(row["normalization_reason"] == reason for row in passed)
            for reason in ("abstain_literal_to_null", "duplicate_supporting_ids", NEW_NORMALIZATION_REASON)
        },
        "quality_metrics_computed": False,
        "quality_claim": "none; M5.3 measures runtime and normalization integrity only",
    }


def normalization_violations(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    violations: dict[str, list[str]] = {}
    for row in records:
        gaps: list[str] = []
        raw = (row.get("raw_model_output") or {}).get("parsed")
        top3_ids = row.get("top3_chunk_ids") or []
        eligible = (
            isinstance(raw, dict)
            and raw.get("decision") == "abstain"
            and not (
                isinstance(raw.get("answer"), str)
                and raw["answer"].strip().lower() == "null"
                and raw.get("supporting_chunk_ids") == []
            )
            and (
                raw.get("answer") is None
                or (isinstance(raw.get("answer"), str) and bool(raw["answer"].strip()))
            )
            and isinstance(raw.get("supporting_chunk_ids"), list)
            and all(isinstance(chunk_id, str) for chunk_id in raw["supporting_chunk_ids"])
            and set(raw["supporting_chunk_ids"]).issubset(set(top3_ids))
            and (raw.get("answer") is not None or bool(raw["supporting_chunk_ids"]))
        )
        applied = row.get("normalization_reason") == NEW_NORMALIZATION_REASON
        if eligible and not applied:
            gaps.append("eligible_vi_abstain_was_not_canonicalized")
        if applied and not eligible:
            gaps.append("new_rule_applied_outside_declared_eligibility")
        if applied:
            if row.get("normalization_applied") is not True:
                gaps.append("new_rule_reason_without_applied_audit_flag")
            if not isinstance(raw, dict) or raw.get("decision") != "abstain":
                gaps.append("new_rule_without_raw_abstain")
            if row.get("decision") != "abstain" or row.get("answer") is not None:
                gaps.append("new_rule_without_canonical_abstain_response")
            if row.get("supporting_chunk_ids") or row.get("citations"):
                gaps.append("new_rule_left_evidence_or_citations")
            normalized = row.get("normalized_output")
            if (
                not isinstance(normalized, dict)
                or normalized.get("decision") != "abstain"
                or normalized.get("answer") is not None
                or normalized.get("supporting_chunk_ids") != []
            ):
                gaps.append("new_rule_normalized_shape_invalid")
        if gaps:
            violations[row["intent_id"]] = gaps
    return violations


def evaluate_gates(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    runtime_mismatches_after: list[str],
    scope_after: dict[str, Any],
    declared_ids: list[str],
) -> dict[str, Any]:
    observed_ids = [row["intent_id"] for row in records]
    stage_totals = {
        "translation": sum(row["translation_call_count"] for row in records),
        "retrieval": sum(row["retrieval_call_count"] for row in records),
        "generation": sum(row["generation_call_count"] for row in records),
    }
    non_single_stage_calls = {
        row["intent_id"]: {
            "translation": row["translation_call_count"],
            "retrieval": row["retrieval_call_count"],
            "generation": row["generation_call_count"],
        }
        for row in records
        if any(
            row[field] != 1
            for field in ("translation_call_count", "retrieval_call_count", "generation_call_count")
        )
    }
    diagnostic = {row["intent_id"]: diagnostic_gaps(row) for row in records if diagnostic_gaps(row)}
    g1 = (
        observed_ids == declared_ids
        and len(records) == EXPECTED_INTENT_COUNT
        and all(value == EXPECTED_INTENT_COUNT for value in stage_totals.values())
        and not non_single_stage_calls
        and not diagnostic
        and not runtime_mismatches_after
    )
    g2 = summary["total_runtime_failure_count"] == 0
    g3 = scope_after["result"] == "PASS"
    norm_violations = normalization_violations(records)
    g4 = not norm_violations
    conditions = {
        "G1_execution_integrity": {
            "result": "PASS" if g1 else "FAIL",
            "intent_ids_match_preregistered_order": observed_ids == declared_ids,
            "record_count": len(records),
            "stage_call_totals": stage_totals,
            "records_with_non_single_stage_calls": non_single_stage_calls,
            "diagnostic_gaps_by_intent": diagnostic,
            "runtime_mismatches_after_execution": runtime_mismatches_after,
        },
        "G2_runtime_failure": {
            "result": "PASS" if g2 else "FAIL",
            "total_runtime_failure_count": summary["total_runtime_failure_count"],
            "failure_layer_counts": summary["failure_layer_counts"],
        },
        "G3_scope_integrity": {"result": "PASS" if g3 else "FAIL", **scope_after},
        "G4_normalization_integrity": {
            "result": "PASS" if g4 else "FAIL",
            "new_rule": NEW_NORMALIZATION_REASON,
            "normalization_reason_counts": summary["normalization_reason_counts"],
            "violations_by_intent": norm_violations,
        },
    }
    return {
        "all_passed": all(item["result"] == "PASS" for item in conditions.values()),
        "pass_rule": "G1, G2, G3 and G4 must all PASS",
        "conditions": conditions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify pins without loading encoder or Ollama.")
    args = parser.parse_args()

    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if prereg["status"] != "preregistered_not_executed":
        raise ValueError("M5.3 pre-registration is not in pre-execution state")
    verify_frozen_inputs(prereg)
    verify_runtime_sources(prereg)
    verify_analysis_code(prereg)
    scope_before = scope_integrity_report(prereg)
    if scope_before["result"] != "PASS":
        raise ValueError("M5.3 scope integrity failed before execution")
    intents = load_jsonl(M1_ARTIFACT)
    declared_ids = prereg["execution_order"]["intent_ids"]
    if [row["intent_id"] for row in intents] != declared_ids:
        raise ValueError("M5.3 intent order differs from pre-registration")

    prereg_hash = sha256_file(PREREGISTRATION)
    print(f"Pre-registration verified: {prereg_hash}")
    print(f"Frozen inputs verified   : {len(prereg['frozen_inputs_sha256'])}")
    print(f"Runtime sources verified : {len(prereg['runtime_under_test']['source_sha256_lf_normalized'])}")
    print(f"Analysis scripts verified: {len(prereg['analysis_code_sha256_lf_normalized'])}")
    print(f"Scope integrity          : {scope_before['result']}")
    print(f"Execution order verified : {len(declared_ids)} intents")
    if args.verify_only:
        print("verify-only: no encoder load and no Ollama call was made.")
        return

    ensure_no_existing_result_artifacts()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    search = RecordingSearchService(DenseSearchService.load())
    translator = RecordingTranslator(build_default_translation_provider())
    generator = RecordingGenerationProvider(build_default_provider())
    service = GroundedAnswerService(search_service=search, provider=generator, translator=translator)
    records = run_execution(service, translator, search, generator, intents)
    mismatches_after = runtime_source_mismatches(prereg)
    scope_after = scope_integrity_report(prereg)
    summary = summarise(records)
    gates = evaluate_gates(records, summary, mismatches_after, scope_after, declared_ids)
    write_json(GATE_RESULTS, {"summary": summary, "gates": gates})
    manifest = {
        "schema_version": "multilingual_runtime_v1_m5_3_execution_manifest_v1",
        "milestone": "multilingual_runtime_v1_m5",
        "stage": "m5.3",
        "attempt_id": ATTEMPT_ID,
        "status": "executed_complete" if len(records) == EXPECTED_INTENT_COUNT else "executed_incomplete",
        "preregistration": {
            "file": "reports/34_multilingual_runtime_v1_m5_3/m5_3_preregistration.json",
            "sha256": prereg_hash,
        },
        "execution": {
            "expected_intent_count": EXPECTED_INTENT_COUNT,
            "executed_intent_count": len(records),
            "passed_count": summary["passed_count"],
            "total_runtime_failure_count": summary["total_runtime_failure_count"],
            "translation_call_count": sum(row["translation_call_count"] for row in records),
            "retrieval_call_count": sum(row["retrieval_call_count"] for row in records),
            "generation_call_count": sum(row["generation_call_count"] for row in records),
            "retry_count": 0,
            "continued_after_failure": True,
            "raw_output_flushed_after_each_intent": True,
        },
        "gates": gates,
        "scope_integrity_before_execution": scope_before,
        "scope_integrity_after_execution": scope_after,
        "runtime_sources_after_execution": {
            "rehashed": True,
            "mismatched_sources": mismatches_after,
            "result": "PASS" if not mismatches_after else "FAIL",
        },
        "ground_truth_exposed_to_runtime_calls": False,
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "output_artifacts": [
            {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
            for path in (RUNTIME_OUTPUTS, GATE_RESULTS)
        ],
        "validation_status": "passed" if gates["all_passed"] else "failed_gates",
    }
    write_json(EXECUTION_MANIFEST, manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(json.dumps(gates, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
