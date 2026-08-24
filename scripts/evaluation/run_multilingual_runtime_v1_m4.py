"""Multilingual Runtime V1 - M4: measure the Vietnamese runtime failure rate.

M3 attempt 1 used stop-on-first-failure. It halted at the second intent, produced 2 of
20 records and could not estimate anything. M4 changes the instrument, not the runtime:
every intent is executed, a failure is recorded with full diagnostics, and execution
continues.

The runtime under test is byte-identical to the one M3 pinned. Nothing here changes a
prompt, a model, the retriever or the normalization rules. Diagnostics come from pure
delegation wrappers around the pinned translator, search service and generation
provider, with the exception chain as a fallback. Both mechanisms observe the runtime
without altering it.

Raw output is flushed atomically after every intent, runtime source hashes are
re-verified after execution, and the four pre-registered integrity conditions are
evaluated and recorded.

M4 makes no claim about Vietnamese answer quality. It measures how often the runtime
fails and at which layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.run_multilingual_runtime_v1_m3 import wilson_interval  # noqa: E402
from src.grounded_answer.ollama_provider import GroundedAnswerProviderError  # noqa: E402
from src.grounded_answer.provider import GenerationProviderResult  # noqa: E402
from src.grounded_answer.service import (  # noqa: E402
    GroundedAnswerContractError,
    GroundedAnswerService,
    build_default_provider,
)
from src.multilingual.translation import (  # noqa: E402
    TranslationContractError,
    TranslationError,
    TranslationProviderError,
    build_default_translation_provider,
)
from src.search_api.service import DenseSearchService  # noqa: E402

REPORT_DIR = PROJECT_ROOT / "reports/32_multilingual_runtime_v1_m4"
PREREGISTRATION = REPORT_DIR / "m4_preregistration.json"
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"

RUNTIME_OUTPUTS = REPORT_DIR / "m4_runtime_outputs.jsonl"
FAILURE_SUMMARY = REPORT_DIR / "m4_failure_summary.json"
EXECUTION_MANIFEST = REPORT_DIR / "m4_execution_manifest.json"
RESULT_ARTIFACT_NAMES = (
    "m4_runtime_outputs.jsonl",
    "m4_failure_summary.json",
    "m4_execution_manifest.json",
)

ATTEMPT_ID = "m4-attempt-1"
EXPECTED_INTENT_COUNT = 20
ANSWER_LANGUAGE = "vi"

FAILURE_LAYERS = (
    "translation_contract",
    "translation_provider",
    "translation_other",
    "generation_contract",
    "generation_provider",
    "runtime_other",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    """Replace the file in one step so an interruption never leaves a torn record."""

    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class _Recorder:
    """Shared bookkeeping for the pure delegation wrappers."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.call_count = 0
        self.latency_ms: float | None = None

    def reset(self) -> None:
        self.call_count = 0
        self.latency_ms = None


class RecordingTranslator(_Recorder):
    """Records the translation and its telemetry; returns the inner result unchanged."""

    def __init__(self, inner: Any) -> None:
        super().__init__(inner)
        self.last_result: Any = None

    def reset(self) -> None:
        super().reset()
        self.last_result = None

    def translate(self, question_vi: str) -> Any:
        self.call_count += 1
        started = time.perf_counter()
        try:
            result = self.inner.translate(question_vi)
        finally:
            self.latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        self.last_result = result
        return result


class RecordingSearchService(_Recorder):
    """Records the Dense Top 3; returns the inner result unchanged."""

    def __init__(self, inner: Any) -> None:
        super().__init__(inner)
        self.last_results: list[dict[str, Any]] | None = None

    def reset(self) -> None:
        super().reset()
        self.last_results = None

    @property
    def index_run_id(self) -> str:
        return self.inner.index_run_id

    def search(self, query: str) -> list[dict[str, Any]]:
        self.call_count += 1
        started = time.perf_counter()
        try:
            results = self.inner.search(query)
        finally:
            self.latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        self.last_results = results
        return results


class RecordingGenerationProvider(_Recorder):
    """Records the raw generator payload and token counters before strict validation.

    The service validates the payload after this call returns, so a contract failure
    downstream no longer costs the diagnostics: the raw content and the token counters
    are already captured here.
    """

    def __init__(self, inner: Any) -> None:
        super().__init__(inner)
        self.last_result: GenerationProviderResult | None = None

    def reset(self) -> None:
        super().reset()
        self.last_result = None

    def verify_runtime(self) -> dict[str, Any]:
        return self.inner.verify_runtime()

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> GenerationProviderResult:
        self.call_count += 1
        started = time.perf_counter()
        try:
            result = self.inner.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
            )
        finally:
            self.latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        self.last_result = result
        return result


def verify_frozen_inputs(prereg: dict[str, Any]) -> None:
    for relative_path, expected in prereg["frozen_inputs_sha256"].items():
        if sha256_file(PROJECT_ROOT / relative_path) != expected:
            raise ValueError(f"Pre-registered input changed since pre-registration: {relative_path}")


def runtime_source_mismatches(prereg: dict[str, Any]) -> list[str]:
    """Return the runtime sources whose hash no longer matches the pre-registration."""

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
    """Return the analysis scripts whose hash no longer matches the pre-registration.

    The pre-registration pins this runner and the M3 runner it imports for the Wilson
    interval. Without this check the measurement code could drift between
    pre-registration and execution exactly the way the runtime could before I4.
    """

    expected_map = prereg["analysis_code_sha256_lf_normalized"]
    if not expected_map:
        raise ValueError("Pre-registration does not pin any analysis script")
    return [
        relative_path
        for relative_path, expected in expected_map.items()
        if sha256_file_lf(PROJECT_ROOT / relative_path) != expected
    ]


def verify_analysis_code(prereg: dict[str, Any]) -> None:
    """Refuse to run if the measurement code changed after pre-registration.

    This detects drift, not a determined adversary: an edit that also rewrites the
    pre-registration passes. Its purpose is that nobody, including the author, can
    quietly change how the numbers are produced between registering and running.
    """

    mismatches = analysis_code_mismatches(prereg)
    if mismatches:
        raise ValueError("Analysis code changed since pre-registration: " + ", ".join(mismatches))


def ensure_no_existing_result_artifacts() -> None:
    existing = [name for name in RESULT_ARTIFACT_NAMES if (REPORT_DIR / name).exists()]
    if existing:
        raise FileExistsError("M4 result artifacts already exist: " + ", ".join(existing))


def classify_failure(error: BaseException) -> str:
    """Map an exception to the pre-registered failure layer."""

    if isinstance(error, TranslationContractError):
        return "translation_contract"
    if isinstance(error, TranslationProviderError):
        return "translation_provider"
    if isinstance(error, TranslationError):
        return "translation_other"
    if isinstance(error, GroundedAnswerContractError):
        return "generation_contract"
    if isinstance(error, GroundedAnswerProviderError):
        return "generation_provider"
    return "runtime_other"


def extract_raw_model_output(error: BaseException) -> dict[str, Any] | None:
    """Fallback capture from the exception chain when the recorder holds nothing.

    ``str(ValidationError)`` truncates the payload, but ``errors()[0]["input"]`` holds
    it in full. A JSON decode failure keeps the unparsed text on ``doc``.
    """

    cause = error.__cause__
    if isinstance(cause, ValidationError):
        entries = cause.errors()
        if entries and "input" in entries[0]:
            return {"capture": "validation_error_input", "payload": entries[0]["input"]}
        return None
    if isinstance(cause, json.JSONDecodeError):
        return {"capture": "json_decode_error_doc", "payload": cause.doc}
    return None


def raw_output_from_recorder(generator: RecordingGenerationProvider) -> dict[str, Any] | None:
    """Preferred capture: the exact provider payload, parsed when it is valid JSON."""

    result = generator.last_result
    if result is None:
        return None
    try:
        parsed: Any | None = json.loads(result.content)
    except json.JSONDecodeError:
        parsed = None
    return {"capture": "generation_provider_recorder", "content": result.content, "parsed": parsed}


def evidence_from_results(results: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not results:
        return []
    return [
        {
            "rank": int(item["rank"]),
            "chunk_id": str(item["chunk_id"]),
            "score": float(item["score"]),
            "video_id": str(item["video_id"]),
            "start_second": float(item["start_second"]),
            "end_second": float(item["end_second"]),
        }
        for item in results
    ]


def stage_telemetry(
    translator: RecordingTranslator,
    search: RecordingSearchService,
    generator: RecordingGenerationProvider,
) -> dict[str, Any]:
    """Per-stage latency and token counters, identical on the success and failure paths."""

    translation = translator.last_result
    generation = generator.last_result
    evidence = evidence_from_results(search.last_results)
    return {
        "retrieval_query": translation.literal_en if translation is not None else None,
        "translation_call_count": translator.call_count,
        "translation_latency_ms": translator.latency_ms,
        "translation_prompt_eval_count": translation.prompt_eval_count if translation is not None else None,
        "translation_eval_count": translation.eval_count if translation is not None else None,
        "retrieval_call_count": search.call_count,
        "retrieval_latency_ms": search.latency_ms,
        "top3_evidence": evidence,
        "top3_chunk_ids": [item["chunk_id"] for item in evidence],
        "generation_call_count": generator.call_count,
        "generation_latency_ms": generator.latency_ms,
        "generation_prompt_eval_count": generation.prompt_eval_count if generation is not None else None,
        "generation_eval_count": generation.eval_count if generation is not None else None,
    }


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
        "schema_version": "multilingual_runtime_v1_m4_output_v2",
        "execution_attempt_id": ATTEMPT_ID,
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
            print(
                f"  {record['intent_id']} {record['runtime_status']:7} {layer:22} "
                f"{record['total_latency_ms']:9.1f}ms"
            )
    return records


def evaluate_integrity_conditions(
    records: list[dict[str, Any]],
    runtime_mismatches_after_execution: list[str],
    expected_intent_count: int = EXPECTED_INTENT_COUNT,
) -> dict[str, Any]:
    """Evaluate the pre-registered I1-I4. None of these is a promotion gate."""

    failed = [row for row in records if row["runtime_status"] != "passed"]
    i1 = len(records) == expected_intent_count
    i2 = len({row["intent_id"] for row in records}) == len(records) and all(
        row["translation_call_count"] <= 1
        and row["retrieval_call_count"] <= 1
        and row["generation_call_count"] <= 1
        for row in records
    )
    i3 = all(
        bool(row["failure_layer"])
        and bool(row["error_type"])
        and (row["generation_call_count"] == 0 or row["raw_model_output"] is not None)
        for row in failed
    )
    i4 = not runtime_mismatches_after_execution
    conditions = {
        "I1": {"condition": "all intents attempted and recorded", "result": "PASS" if i1 else "FAIL",
               "observed_record_count": len(records), "expected_record_count": expected_intent_count},
        "I2": {"condition": "no retry and at most one call per stage per intent", "result": "PASS" if i2 else "FAIL"},
        "I3": {"condition": "failed records keep layer, error type and raw payload when generation ran",
               "result": "PASS" if i3 else "FAIL", "failed_record_count": len(failed)},
        "I4": {"condition": "runtime source hashes still match after execution", "result": "PASS" if i4 else "FAIL",
               "mismatched_sources": runtime_mismatches_after_execution},
    }
    return {
        "all_passed": all(entry["result"] == "PASS" for entry in conditions.values()),
        "conditions": conditions,
    }


def summarise(records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [row for row in records if row["runtime_status"] == "passed"]
    failed = [row for row in records if row["runtime_status"] != "passed"]
    total = len(records)
    layer_counts = {layer: sum(1 for row in failed if row["failure_layer"] == layer) for layer in FAILURE_LAYERS}
    success_low, success_high = wilson_interval(len(passed), total)
    failure_low, failure_high = wilson_interval(len(failed), total)
    decisions = [row["decision"] for row in passed]

    def latency_stats(field: str) -> dict[str, float] | None:
        values = [row[field] for row in records if row.get(field) is not None]
        if not values:
            return None
        return {
            "count": len(values),
            "mean_ms": round(sum(values) / len(values), 3),
            "max_ms": max(values),
        }

    def token_total(field: str) -> int | None:
        values = [row[field] for row in records if row.get(field) is not None]
        return sum(values) if values else None

    return {
        "schema_version": "multilingual_runtime_v1_m4_failure_summary_v2",
        "attempt_id": ATTEMPT_ID,
        "executed_intent_count": total,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "runtime_success_rate": {
            "numerator": len(passed),
            "denominator": total,
            "rate": round(len(passed) / total, 9) if total else None,
            "wilson_95": [success_low, success_high],
        },
        "runtime_failure_rate": {
            "numerator": len(failed),
            "denominator": total,
            "rate": round(len(failed) / total, 9) if total else None,
            "wilson_95": [failure_low, failure_high],
        },
        "failure_layer_counts": layer_counts,
        "failed_intent_ids": [row["intent_id"] for row in failed],
        "raw_model_output_captured_on_failure": sum(1 for row in failed if row["raw_model_output"]),
        "retrieval_query_captured_on_failure": sum(1 for row in failed if row["retrieval_query"]),
        "top3_captured_on_failure": sum(1 for row in failed if row["top3_chunk_ids"]),
        "generation_telemetry_captured_on_failure": sum(
            1 for row in failed if row.get("generation_call_count") and row.get("generation_eval_count") is not None
        ),
        "decision_counts_among_passed": {
            value: sum(1 for decision in decisions if decision == value) for value in ("answer", "abstain")
        },
        "stage_latency": {
            "translation": latency_stats("translation_latency_ms"),
            "retrieval": latency_stats("retrieval_latency_ms"),
            "generation": latency_stats("generation_latency_ms"),
            "total": latency_stats("total_latency_ms"),
        },
        "token_totals": {
            "translation_prompt_eval": token_total("translation_prompt_eval_count"),
            "translation_eval": token_total("translation_eval_count"),
            "generation_prompt_eval": token_total("generation_prompt_eval_count"),
            "generation_eval": token_total("generation_eval_count"),
        },
        "quality_metrics_computed": False,
        "quality_claim": "none; M4 measures runtime failure only",
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
    integrity = evaluate_integrity_conditions(records, mismatches_after)
    summary = summarise(records)
    write_json(FAILURE_SUMMARY, summary)

    manifest = {
        "schema_version": "multilingual_runtime_v1_m4_execution_manifest_v2",
        "milestone": "multilingual_runtime_v1_m4",
        "attempt_id": ATTEMPT_ID,
        "status": "executed_complete" if len(records) == EXPECTED_INTENT_COUNT else "executed_incomplete",
        "preregistration": {
            "file": "reports/32_multilingual_runtime_v1_m4/m4_preregistration.json",
            "revision": prereg["preregistration_revision"],
            "sha256": prereg_hash,
        },
        "execution": {
            "expected_intent_count": EXPECTED_INTENT_COUNT,
            "executed_intent_count": len(records),
            "passed_count": summary["passed_count"],
            "failed_count": summary["failed_count"],
            "translation_call_count": sum(row["translation_call_count"] for row in records),
            "retrieval_call_count": sum(row["retrieval_call_count"] for row in records),
            "generation_call_count": sum(row["generation_call_count"] for row in records),
            "retry_count": 0,
            "continued_after_failure": True,
            "raw_output_flushed_after_each_intent": True,
        },
        "integrity_conditions": integrity,
        "runtime_sources_after_execution": {
            "rehashed": True,
            "mismatched_sources": mismatches_after,
            "result": "PASS" if not mismatches_after else "FAIL",
        },
        "frozen_inputs_sha256": prereg["frozen_inputs_sha256"],
        "runtime_under_test_sha256_lf_normalized": prereg["runtime_under_test"]["source_sha256_lf_normalized"],
        "analysis_code_sha256_lf_normalized": prereg["analysis_code_sha256_lf_normalized"],
        "analysis_code_verification": {
            "verified_before_any_model_call": True,
            "scripts_checked": sorted(prereg["analysis_code_sha256_lf_normalized"]),
            "detects": "drift between pre-registration and execution, not a rewrite that also updates the pre-registration",
        },
        "ground_truth_exposed_to_runtime_calls": False,
        "quality_metrics_computed": False,
        "human_review_performed": False,
        "output_artifacts": [
            {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
            for path in (RUNTIME_OUTPUTS, FAILURE_SUMMARY)
        ],
        "validation_status": "passed" if integrity["all_passed"] else "failed_integrity_conditions",
    }
    write_json(EXECUTION_MANIFEST, manifest)

    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print()
    print(json.dumps(integrity, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
