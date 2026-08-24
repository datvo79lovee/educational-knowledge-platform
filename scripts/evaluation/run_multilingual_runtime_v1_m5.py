"""Multilingual Runtime V1 - M5.1: test one conditional Vietnamese abstention prompt.

M4 froze an observation: 8 of 20 records failed, every one of them at
``generation_contract``, and every failing payload had chosen ``decision="abstain"``.
M5.1 tests whether one narrow prompt change removes those contract violations. It is a
hypothesis test, not a conclusion carried over from M4.

One prompt artifact change is authorised, comprising exactly two symbols:
``VI_SYSTEM_PROMPT``, the single behavioural change, and ``VI_PROMPT_VERSION``, which
carries identity and provenance only. The runner proves that at execution time by
comparing every runtime source hash against the M4 pins and by checking each pinned
symbol inside the prompt module individually, so nothing can hide behind the authorised
filename.

The measurement machinery is imported from the M4 runner rather than reimplemented, so
the two milestones capture and classify failures identically.
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
from src.grounded_answer.prompts import (  # noqa: E402
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    VI_PROMPT_VERSION,
    VI_SYSTEM_PROMPT,
    build_user_prompt,
)
from src.grounded_answer.service import GroundedAnswerService, build_default_provider  # noqa: E402
from src.multilingual.translation import build_default_translation_provider  # noqa: E402
from src.search_api.service import DenseSearchService  # noqa: E402

REPORT_DIR = PROJECT_ROOT / "reports/33_multilingual_runtime_v1_m5"
PREREGISTRATION = REPORT_DIR / "m5_preregistration.json"
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"

RUNTIME_OUTPUTS = REPORT_DIR / "m5_1_runtime_outputs.jsonl"
GATE_RESULTS = REPORT_DIR / "m5_1_gate_results.json"
EXECUTION_MANIFEST = REPORT_DIR / "m5_1_execution_manifest.json"
RESULT_ARTIFACT_NAMES = (
    "m5_1_runtime_outputs.jsonl",
    "m5_1_gate_results.json",
    "m5_1_execution_manifest.json",
)

ATTEMPT_ID = "m5-1-attempt-1"
EXPECTED_INTENT_COUNT = 20
ANSWER_LANGUAGE = "vi"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_frozen_inputs(prereg: dict[str, Any]) -> None:
    for relative_path, expected in prereg["frozen_inputs_sha256"].items():
        if sha256_file(PROJECT_ROOT / relative_path) != expected:
            raise ValueError(f"Pre-registered input changed since pre-registration: {relative_path}")


def runtime_source_mismatches(prereg: dict[str, Any]) -> list[str]:
    expected_map = prereg["runtime_under_test"]["source_sha256_lf_normalized"]
    if not expected_map:
        raise ValueError("Pre-registration does not pin any runtime source")
    return [
        relative_path
        for relative_path, expected in expected_map.items()
        if sha256_file_lf(PROJECT_ROOT / relative_path) != expected
    ]


def verify_runtime_sources(prereg: dict[str, Any]) -> None:
    mismatches = runtime_source_mismatches(prereg)
    if mismatches:
        raise ValueError("Runtime under test changed since pre-registration: " + ", ".join(mismatches))


def analysis_code_mismatches(prereg: dict[str, Any]) -> list[str]:
    expected_map = prereg["analysis_code_sha256_lf_normalized"]
    if not expected_map:
        raise ValueError("Pre-registration does not pin any analysis script")
    return [
        relative_path
        for relative_path, expected in expected_map.items()
        if sha256_file_lf(PROJECT_ROOT / relative_path) != expected
    ]


def verify_analysis_code(prereg: dict[str, Any]) -> None:
    mismatches = analysis_code_mismatches(prereg)
    if mismatches:
        raise ValueError("Analysis code changed since pre-registration: " + ", ".join(mismatches))


def prompt_symbol_report(prereg: dict[str, Any]) -> dict[str, Any]:
    """Check every pinned symbol inside the authorised prompt module, one by one.

    File-level authorisation is not enough: ``prompts.py`` also holds the frozen English
    prompt, the English version label and ``build_user_prompt``. Without per-symbol pins
    an unrelated edit could hide behind the authorised filename.
    """

    pins = prereg["scope_integrity"]["prompt_symbols"]
    observed = {
        "en_system_prompt_sha256": sha256_text(SYSTEM_PROMPT),
        "en_prompt_version": PROMPT_VERSION,
        "build_user_prompt_source_sha256": sha256_text(
            inspect.getsource(build_user_prompt).replace("\r\n", "\n")
        ),
        "vi_system_prompt_sha256": sha256_text(VI_SYSTEM_PROMPT),
        "vi_prompt_version": VI_PROMPT_VERSION,
    }
    frozen_symbols = ("en_system_prompt_sha256", "en_prompt_version", "build_user_prompt_source_sha256")
    candidate_symbols = ("vi_system_prompt_sha256", "vi_prompt_version")
    symbols = {
        name: {
            "role": "frozen" if name in frozen_symbols else "authorized_candidate",
            "expected": pins[name],
            "observed": observed[name],
            "result": "PASS" if observed[name] == pins[name] else "FAIL",
        }
        for name in frozen_symbols + candidate_symbols
    }
    failed = sorted(name for name, entry in symbols.items() if entry["result"] == "FAIL")
    return {
        "symbols": symbols,
        "mismatched_symbols": failed,
        "frozen_symbols_unchanged": not [name for name in failed if name in frozen_symbols],
        "result": "PASS" if not failed else "FAIL",
    }


def scope_integrity_report(prereg: dict[str, Any]) -> dict[str, Any]:
    """Prove that only the authorised prompt artifact changed relative to M4.

    Two independent layers: every runtime source hash is compared against the M4 pin so
    that exactly the authorised file may differ, and every pinned symbol inside that file
    is checked individually so a change cannot hide behind the authorised filename.
    """

    scope = prereg["scope_integrity"]
    baseline = scope["baseline_runtime_sources_sha256_lf_normalized"]
    authorised = list(scope["authorized_changed_files"])

    changed = [
        relative_path
        for relative_path, expected in baseline.items()
        if sha256_file_lf(PROJECT_ROOT / relative_path) != expected
    ]
    unauthorised = sorted(set(changed) - set(authorised))
    missing_change = sorted(set(authorised) - set(changed))
    symbols = prompt_symbol_report(prereg)

    return {
        "baseline_milestone": scope.get("baseline_milestone", "multilingual_runtime_v1_m4"),
        "authorized_changed_files": authorised,
        "observed_changed_files": sorted(changed),
        "unauthorized_changed_files": unauthorised,
        "authorized_files_without_change": missing_change,
        "prompt_symbols": symbols,
        "en_system_prompt_sha256": symbols["symbols"]["en_system_prompt_sha256"]["observed"],
        "en_system_prompt_unchanged": symbols["symbols"]["en_system_prompt_sha256"]["result"] == "PASS",
        "vi_prompt_version": VI_PROMPT_VERSION,
        "vi_system_prompt_sha256": symbols["symbols"]["vi_system_prompt_sha256"]["observed"],
        "result": "PASS" if not unauthorised and symbols["result"] == "PASS" else "FAIL",
    }


def ensure_no_existing_result_artifacts() -> None:
    existing = [name for name in RESULT_ARTIFACT_NAMES if (REPORT_DIR / name).exists()]
    if existing:
        raise FileExistsError("M5.1 result artifacts already exist: " + ", ".join(existing))


def execute_intent(
    service: GroundedAnswerService,
    translator: RecordingTranslator,
    search: RecordingSearchService,
    generator: RecordingGenerationProvider,
    intent: dict[str, Any],
) -> dict[str, Any]:
    """Run one intent. A failure is recorded as data; execution never retries."""

    translator.reset()
    search.reset()
    generator.reset()
    started = time.perf_counter()
    record: dict[str, Any] = {
        "schema_version": "multilingual_runtime_v1_m5_1_output_v1",
        "execution_attempt_id": ATTEMPT_ID,
        "vi_prompt_version": VI_PROMPT_VERSION,
        "intent_id": intent["intent_id"],
        "original_query": intent["question_vi"],
        "answer_language": ANSWER_LANGUAGE,
    }
    try:
        execution = service.answer(intent["question_vi"], ANSWER_LANGUAGE)
    except Exception as error:  # noqa: BLE001 - every failure is evaluation data
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        record.update(stage_telemetry(translator, search, generator))
        record.update(
            {
                "runtime_status": "failed",
                "failure_layer": classify_failure(error),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
                "raw_model_output": raw_output_from_recorder(generator) or extract_raw_model_output(error),
                "decision": None,
                "answer": None,
                "supporting_chunk_ids": [],
                "citations": [],
                "normalization_applied": None,
                "normalization_reason": None,
                "index_run_id": None,
                "total_latency_ms": elapsed_ms,
            }
        )
        return record

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    response = execution.response
    record.update(stage_telemetry(translator, search, generator))
    record.update(
        {
            "runtime_status": "passed",
            "failure_layer": None,
            "error_type": None,
            "error_message": None,
            "cause_type": None,
            "raw_model_output": raw_output_from_recorder(generator),
            "decision": response.decision,
            "answer": response.answer,
            "supporting_chunk_ids": list(response.supporting_chunk_ids),
            "citations": [citation.model_dump() for citation in response.citations],
            "normalization_applied": execution.normalization_applied,
            "normalization_reason": execution.normalization_reason,
            "index_run_id": execution.index_run_id,
            "total_latency_ms": elapsed_ms,
        }
    )
    return record


def run_execution(
    service: GroundedAnswerService,
    translator: RecordingTranslator,
    search: RecordingSearchService,
    generator: RecordingGenerationProvider,
    intents: list[dict[str, Any]],
    outputs_path: Path,
    announce: bool = True,
) -> list[dict[str, Any]]:
    """Execute every intent, flushing the raw output atomically after each one."""

    records: list[dict[str, Any]] = []
    for intent in intents:
        record = execute_intent(service, translator, search, generator, intent)
        records.append(record)
        write_jsonl_atomic(outputs_path, records)
        if announce:
            layer = record["failure_layer"] or "-"
            decision = record["decision"] or "-"
            print(
                f"  {record['intent_id']} {record['runtime_status']:7} {decision:8} {layer:22} "
                f"{record['total_latency_ms']:9.1f}ms"
            )
    return records


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [row for row in records if row["runtime_status"] == "passed"]
    failed = [row for row in records if row["runtime_status"] != "passed"]
    total = len(records)
    layer_counts = {layer: sum(1 for row in failed if row["failure_layer"] == layer) for layer in FAILURE_LAYERS}
    decisions = [row["decision"] for row in passed]
    failure_low, failure_high = wilson_interval(len(failed), total) if total else (None, None)

    def latency_stats(field: str) -> dict[str, float] | None:
        values = [row[field] for row in records if row.get(field) is not None]
        if not values:
            return None
        return {"count": len(values), "mean_ms": round(sum(values) / len(values), 3), "max_ms": max(values)}

    return {
        "schema_version": "multilingual_runtime_v1_m5_1_summary_v1",
        "attempt_id": ATTEMPT_ID,
        "vi_prompt_version": VI_PROMPT_VERSION,
        "executed_intent_count": total,
        "passed_count": len(passed),
        "total_runtime_failure_count": len(failed),
        "runtime_failure_rate": {
            "numerator": len(failed),
            "denominator": total,
            "rate": round(len(failed) / total, 9) if total else None,
            "wilson_95": [failure_low, failure_high],
        },
        "failure_layer_counts": layer_counts,
        "failed_intent_ids": [row["intent_id"] for row in failed],
        "decision_counts_among_passed": {
            value: sum(1 for decision in decisions if decision == value) for value in ("answer", "abstain")
        },
        "valid_abstention_count": sum(1 for decision in decisions if decision == "abstain"),
        "raw_model_output_captured_on_failure": sum(1 for row in failed if row["raw_model_output"]),
        "retrieval_query_captured_on_failure": sum(1 for row in failed if row["retrieval_query"]),
        "top3_captured_on_failure": sum(1 for row in failed if row["top3_chunk_ids"]),
        "generation_telemetry_captured_on_failure": sum(
            1 for row in failed if row.get("generation_call_count") and row.get("generation_eval_count") is not None
        ),
        "stage_latency": {
            "translation": latency_stats("translation_latency_ms"),
            "retrieval": latency_stats("retrieval_latency_ms"),
            "generation": latency_stats("generation_latency_ms"),
            "total": latency_stats("total_latency_ms"),
        },
        "quality_metrics_computed": False,
        "quality_claim": "none; M5.1 tests abstention contract compliance only",
    }


def diagnostic_gaps(record: dict[str, Any]) -> list[str]:
    """Name every required diagnostic this record is missing.

    Requirements are conditional on which stages actually ran, because the pipeline is
    sequential: retrieval only happens after translation returns, and generation only
    after retrieval returns. Demanding Top 3 from a translation-layer failure would be
    wrong; not demanding it from a generation-layer failure is the M3 data loss.
    """

    gaps: list[str] = []
    if record.get("runtime_status") != "passed":
        if not record.get("failure_layer"):
            gaps.append("failure_layer")
        if not record.get("error_type"):
            gaps.append("error_type")
    if record.get("translation_call_count", 0) >= 1:
        if record.get("translation_latency_ms") is None:
            gaps.append("translation_latency_ms")
    if record.get("retrieval_call_count", 0) >= 1:
        if not record.get("retrieval_query"):
            gaps.append("retrieval_query")
        if record.get("retrieval_latency_ms") is None:
            gaps.append("retrieval_latency_ms")
    if record.get("generation_call_count", 0) >= 1:
        if not record.get("retrieval_query"):
            gaps.append("retrieval_query")
        if not record.get("top3_chunk_ids"):
            gaps.append("top3_chunk_ids")
        if record.get("raw_model_output") is None:
            gaps.append("raw_model_output")
        for field in ("generation_latency_ms", "generation_prompt_eval_count", "generation_eval_count"):
            if record.get(field) is None:
                gaps.append(field)
    return sorted(set(gaps))


def evaluate_gates(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    runtime_mismatches_after_execution: list[str],
    scope: dict[str, Any],
    declared_intent_ids: list[str],
    expected_intent_count: int = EXPECTED_INTENT_COUNT,
) -> dict[str, Any]:
    """Evaluate the pre-registered G1-G3.

    G2 counts every runtime failure, not only ``generation_contract``. A run that traded
    contract failures for translation failures must not pass.
    """

    failed = [row for row in records if row["runtime_status"] != "passed"]
    passed = [row for row in records if row["runtime_status"] == "passed"]
    observed_ids = [row["intent_id"] for row in records]

    complete_records = len(records) == expected_intent_count
    intent_order_matches = observed_ids == list(declared_intent_ids)
    single_calls = all(
        row["translation_call_count"] <= 1
        and row["retrieval_call_count"] <= 1
        and row["generation_call_count"] <= 1
        for row in records
    )
    full_pipeline_on_pass = [
        row["intent_id"]
        for row in passed
        if not (
            row["translation_call_count"] == 1
            and row["retrieval_call_count"] == 1
            and row["generation_call_count"] == 1
        )
    ]
    stage_call_totals = {
        "translation": sum(row["translation_call_count"] for row in records),
        "retrieval": sum(row["retrieval_call_count"] for row in records),
        "generation": sum(row["generation_call_count"] for row in records),
    }
    clean_run = not failed
    stage_totals_complete = (
        all(total == expected_intent_count for total in stage_call_totals.values()) if clean_run else True
    )
    gaps_by_intent = {
        row["intent_id"]: diagnostic_gaps(row) for row in records if diagnostic_gaps(row)
    }
    diagnostics_kept = not gaps_by_intent
    hashes_stable = not runtime_mismatches_after_execution
    g1 = (
        complete_records
        and intent_order_matches
        and single_calls
        and not full_pipeline_on_pass
        and stage_totals_complete
        and diagnostics_kept
        and hashes_stable
    )

    total_failures = summary["total_runtime_failure_count"]
    generation_contract_failures = summary["failure_layer_counts"]["generation_contract"]
    g2 = total_failures == 0

    g3 = scope["result"] == "PASS"

    conditions = {
        "G1_execution_integrity": {
            "result": "PASS" if g1 else "FAIL",
            "complete_records": complete_records,
            "observed_record_count": len(records),
            "expected_record_count": expected_intent_count,
            "intent_ids_match_preregistered_order": intent_order_matches,
            "single_call_per_stage": single_calls,
            "full_pipeline_on_every_passed_record": not full_pipeline_on_pass,
            "passed_records_missing_a_stage_call": full_pipeline_on_pass,
            "stage_call_totals": stage_call_totals,
            "stage_totals_complete_when_run_is_clean": stage_totals_complete,
            "diagnostics_retained": diagnostics_kept,
            "diagnostic_gaps_by_intent": gaps_by_intent,
            "runtime_hashes_stable_after_execution": hashes_stable,
            "mismatched_sources_after_execution": runtime_mismatches_after_execution,
        },
        "G2_runtime_failure": {
            "result": "PASS" if g2 else "FAIL",
            "rule": "total_runtime_failure_count must be zero across every failure layer",
            "total_runtime_failure_count": total_failures,
            "generation_contract_failure_count": generation_contract_failures,
            "failure_layer_counts": summary["failure_layer_counts"],
            "note": (
                "Counting only generation_contract would let a run pass while failing at the "
                "translation or provider layer. G2 therefore counts every layer."
            ),
        },
        "G3_scope_integrity": {"result": "PASS" if g3 else "FAIL", **scope},
    }
    return {
        "all_passed": all(entry["result"] == "PASS" for entry in conditions.values()),
        "pass_rule": "G1, G2 and G3 must all PASS",
        "conditions": conditions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Check the pre-registered contract and exit without loading the encoder or calling Ollama.",
    )
    args = parser.parse_args()

    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if prereg["status"] != "preregistered_not_executed":
        raise ValueError("Pre-registration is not in the pre-execution state")
    verify_frozen_inputs(prereg)
    verify_runtime_sources(prereg)
    verify_analysis_code(prereg)
    scope_before = scope_integrity_report(prereg)
    if scope_before["result"] != "PASS":
        raise ValueError(
            "Scope integrity failed before execution: "
            f"unauthorized={scope_before['unauthorized_changed_files']}, "
            f"en_prompt_unchanged={scope_before['en_system_prompt_unchanged']}"
        )
    prereg_hash = sha256_file(PREREGISTRATION)
    intents = load_jsonl(M1_ARTIFACT)
    if len(intents) != EXPECTED_INTENT_COUNT:
        raise ValueError(f"Frozen paired artifact must contain {EXPECTED_INTENT_COUNT} intents")
    declared_order = prereg["execution_order"]["intent_ids"]
    if [intent["intent_id"] for intent in intents] != declared_order:
        raise ValueError("Frozen intent order differs from the pre-registered execution order")

    print(f"Pre-registration revision {prereg['preregistration_revision']} verified: {prereg_hash}")
    print(f"Frozen inputs verified   : {len(prereg['frozen_inputs_sha256'])}")
    print(f"Runtime sources verified : {len(prereg['runtime_under_test']['source_sha256_lf_normalized'])}")
    print(f"Analysis scripts verified: {len(prereg['analysis_code_sha256_lf_normalized'])}")
    print(f"Scope integrity vs M4    : changed={scope_before['observed_changed_files']} "
          f"unauthorized={scope_before['unauthorized_changed_files']} "
          f"en_prompt_unchanged={scope_before['en_system_prompt_unchanged']}")
    print(f"Execution order verified : {len(declared_order)} intents")
    if args.verify_only:
        print("verify-only: contract holds; no encoder load and no Ollama call was made.")
        return

    ensure_no_existing_result_artifacts()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    search = RecordingSearchService(DenseSearchService.load())
    translator = RecordingTranslator(build_default_translation_provider())
    generator = RecordingGenerationProvider(build_default_provider())
    service = GroundedAnswerService(
        search_service=search,
        provider=generator,
        translator=translator,
    )

    records = run_execution(service, translator, search, generator, intents, RUNTIME_OUTPUTS)

    mismatches_after = runtime_source_mismatches(prereg)
    scope_after = scope_integrity_report(prereg)
    summary = summarise(records)
    gates = evaluate_gates(records, summary, mismatches_after, scope_after, declared_order)
    write_json(GATE_RESULTS, {"summary": summary, "gates": gates})

    manifest = {
        "schema_version": "multilingual_runtime_v1_m5_1_execution_manifest_v1",
        "milestone": "multilingual_runtime_v1_m5",
        "stage": "m5.1",
        "attempt_id": ATTEMPT_ID,
        "status": "executed_complete" if len(records) == EXPECTED_INTENT_COUNT else "executed_incomplete",
        "preregistration": {
            "file": "reports/33_multilingual_runtime_v1_m5/m5_preregistration.json",
            "revision": prereg["preregistration_revision"],
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
        "prompt_identity": {
            "en_prompt_version": prereg["scope_integrity"]["prompt_symbols"]["en_prompt_version"],
            "en_system_prompt_sha256": scope_after["en_system_prompt_sha256"],
            "vi_prompt_version": VI_PROMPT_VERSION,
            "vi_system_prompt_sha256": scope_after["vi_system_prompt_sha256"],
        },
        "frozen_inputs_sha256": prereg["frozen_inputs_sha256"],
        "runtime_under_test_sha256_lf_normalized": prereg["runtime_under_test"]["source_sha256_lf_normalized"],
        "analysis_code_sha256_lf_normalized": prereg["analysis_code_sha256_lf_normalized"],
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

    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print()
    print(json.dumps(gates, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
