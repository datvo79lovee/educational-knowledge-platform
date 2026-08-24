"""Run the frozen Vietnamese end-to-end runtime for Multilingual Runtime V1 M3.

The runtime receives only ``question_vi`` and ``answer_language='vi'``. Ground Truth,
expected answer points and prior review labels are joined only after all model calls
have finished, when the human-review worksheet is produced. The script never retries,
repairs, tunes or changes the shipped translator, retriever or G0 generator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.grounded_answer.service import (  # noqa: E402
    GroundedAnswerService,
    build_default_provider,
)
from src.multilingual.translation import build_default_translation_provider  # noqa: E402
from src.search_api.service import DenseSearchService  # noqa: E402


REPORT_DIR = PROJECT_ROOT / "reports/31_multilingual_runtime_v1_m3"
PREREGISTRATION = REPORT_DIR / "m3_preregistration.json"
PAIRED_INTENTS = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
EVALUATION_QUESTIONS = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
ENGLISH_BASELINE = (
    PROJECT_ROOT
    / "reports/25_grounded_answer_reliability_v1/grounded_answer_reliability_v1_final_results.csv"
)
M2_MANIFEST = PROJECT_ROOT / "reports/30_multilingual_runtime_v1_m2/m2_manifest.json"

RAW_OUTPUT = REPORT_DIR / "m3_runtime_outputs.jsonl"
REVIEW_WORKSHEET = REPORT_DIR / "m3_human_review_worksheet.csv"
EXECUTION_MANIFEST = REPORT_DIR / "m3_execution_manifest.json"
ATTEMPT_FAILURE = REPORT_DIR / "m3_execution_attempt_failure.json"
RESULT_ARTIFACTS = (RAW_OUTPUT, REVIEW_WORKSHEET, EXECUTION_MANIFEST, ATTEMPT_FAILURE)

EXPECTED_INTENT_COUNT = 20
PRIMARY_EXCLUDED_IDS = {"mit60001-q-023"}
EXECUTION_ATTEMPT_ID = "m3-attempt-1"
REVIEW_ORDER_SEED = "6000103"
RE_REVIEW_ORDER_SEED = "6000103-rereview"
RE_REVIEW_COUNT = 6
WILSON_Z_95 = 1.959963984540054
REVIEW_FIELDS = (
    "intent_id",
    "evaluation_scope",
    "question_vi",
    "expected_answer_points_json",
    "retrieval_query",
    "top3_evidence_json",
    "decision",
    "answer",
    "selected_citations_json",
    "runtime_status",
    "evidence_sufficiency",
    "decision_judgment",
    "answer_correctness",
    "answer_completeness",
    "groundedness",
    "citation_support_overall",
    "output_language",
    "failure_attribution",
    "reviewer_notes",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def serialize_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(REVIEW_FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def deterministic_intent_order(intent_ids: list[str], seed: str) -> list[str]:
    """Return a cross-version-stable order using the pre-registered SHA-256 rule."""

    return sorted(
        intent_ids,
        key=lambda intent_id: (
            hashlib.sha256(f"{seed}:{intent_id}".encode("utf-8")).hexdigest(),
            intent_id,
        ),
    )


def select_re_review_ids(intent_ids: list[str]) -> list[str]:
    primary_ids = [intent_id for intent_id in intent_ids if intent_id not in PRIMARY_EXCLUDED_IDS]
    return deterministic_intent_order(primary_ids, RE_REVIEW_ORDER_SEED)[:RE_REVIEW_COUNT]


def wilson_interval(
    successes: int, total: int, *, z: float = WILSON_Z_95
) -> tuple[float, float]:
    """Wilson score interval used by the post-review M3 analysis."""

    if total <= 0:
        raise ValueError("Wilson interval requires total > 0")
    if successes < 0 or successes > total:
        raise ValueError("Wilson interval requires 0 <= successes <= total")
    proportion = successes / total
    denominator = 1.0 + (z * z / total)
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * (
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        ** 0.5
        / denominator
    )
    return center - radius, center + radius


def verify_hash_map(values: dict[str, str], *, lf_normalized: bool, label: str) -> None:
    if not values:
        raise ValueError(f"Pre-registration has no {label} hashes")
    for relative_path, expected in values.items():
        path = PROJECT_ROOT / relative_path
        actual = sha256_file_lf(path) if lf_normalized else sha256_file(path)
        if actual != expected:
            raise ValueError(f"{label} changed after pre-registration: {relative_path}")


def selected_inputs() -> tuple[list[dict[str, str]], dict[str, dict[str, Any]]]:
    paired = load_jsonl(PAIRED_INTENTS)
    if len(paired) != EXPECTED_INTENT_COUNT:
        raise ValueError(f"Expected {EXPECTED_INTENT_COUNT} paired intents, found {len(paired)}")
    projected = [
        {"intent_id": str(row["intent_id"]), "question_vi": str(row["question_vi"])}
        for row in paired
    ]
    if len({row["intent_id"] for row in projected}) != EXPECTED_INTENT_COUNT:
        raise ValueError("Paired artifact has missing or duplicate intent IDs")

    questions = {str(row["question_id"]): row for row in load_jsonl(EVALUATION_QUESTIONS)}
    for row in projected:
        source = questions.get(row["intent_id"])
        if source is None or source.get("answerable") is not True or source.get("review_status") != "approved":
            raise ValueError(f"M3 input is not canonical approved-answerable: {row['intent_id']}")
    return projected, questions


def derive_frozen_english_baseline(selected_ids: set[str]) -> dict[str, Any]:
    with ENGLISH_BASELINE.open("r", encoding="utf-8-sig", newline="") as handle:
        selected = [row for row in csv.DictReader(handle) if row["question_id"] in selected_ids]
    if len(selected) != EXPECTED_INTENT_COUNT:
        raise ValueError("Frozen English baseline does not cover all M3 intents")
    excluded = sorted(row["question_id"] for row in selected if row["evaluation_status"] == "excluded")
    if excluded != sorted(PRIMARY_EXCLUDED_IDS):
        raise ValueError(f"Frozen English exclusion set changed: {excluded}")
    evaluated = [row for row in selected if row["evaluation_status"] == "evaluated"]
    return {
        "selected_count": len(selected),
        "evaluated_count": len(evaluated),
        "excluded_intent_ids": excluded,
        "decision_correct_count": sum(row["decision_correct"] == "true" for row in evaluated),
        "answer_count": sum(row["generator_decision"] == "answer" for row in evaluated),
        "strict_answer_success_count": sum(
            row["strict_answer_success"] == "true" for row in evaluated
        ),
        "strict_end_to_end_success_count": sum(
            row["end_to_end_success"] == "true" for row in evaluated
        ),
    }


def verify_preregistration() -> tuple[dict[str, Any], list[dict[str, str]], dict[str, dict[str, Any]]]:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if prereg.get("status") != "preregistered_not_executed":
        raise ValueError("M3 pre-registration is not in the locked pre-execution state")
    verify_hash_map(prereg["frozen_inputs_sha256"], lf_normalized=False, label="Frozen input")
    verify_hash_map(
        prereg["runtime_under_test"]["source_sha256_lf_normalized"],
        lf_normalized=True,
        label="Runtime source",
    )
    verify_hash_map(
        prereg["analysis_code_sha256_lf_normalized"],
        lf_normalized=True,
        label="Analysis code",
    )

    m2 = json.loads(M2_MANIFEST.read_text(encoding="utf-8"))
    if m2.get("status") != "frozen_failed" or m2.get("gate_results", {}).get(
        "vi_runtime_candidate"
    ) != "REJECTED":
        raise ValueError("M2 frozen failure boundary is missing or changed")

    intents, questions = selected_inputs()
    expected_ids = prereg["evaluation_scope"]["selected_intent_ids"]
    if [row["intent_id"] for row in intents] != expected_ids:
        raise ValueError("M3 selected intent order differs from pre-registration")
    baseline = derive_frozen_english_baseline(set(expected_ids))
    if baseline != prereg["frozen_english_matched_baseline"]:
        raise ValueError("Frozen matched English baseline no longer reproduces")
    return prereg, intents, questions


def ensure_no_existing_results() -> None:
    existing = [str(path.relative_to(PROJECT_ROOT)) for path in RESULT_ARTIFACTS if path.exists()]
    if existing:
        raise FileExistsError("M3 result artifacts already exist: " + ", ".join(existing))


class TimedTranslator:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.call_count = 0
        self.last_latency_ms: float | None = None

    def translate(self, question_vi: str) -> Any:
        started = time.perf_counter()
        try:
            return self.delegate.translate(question_vi)
        finally:
            self.call_count += 1
            self.last_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)


class TimedGenerator:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.call_count = 0
        self.last_latency_ms: float | None = None

    def verify_runtime(self) -> dict[str, Any]:
        return self.delegate.verify_runtime()

    def generate(self, *, system_prompt: str, user_prompt: str, output_schema: dict[str, Any]) -> Any:
        started = time.perf_counter()
        try:
            return self.delegate.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
            )
        finally:
            self.call_count += 1
            self.last_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)


def execute_runtime(
    intents: list[dict[str, str]],
    search_service: DenseSearchService,
    translator: TimedTranslator,
    generator: TimedGenerator,
) -> list[dict[str, Any]]:
    service = GroundedAnswerService(
        search_service=search_service,
        provider=generator,
        translator=translator,
    )
    rows: list[dict[str, Any]] = []
    for intent in intents:
        translator_before = translator.call_count
        generator_before = generator.call_count
        translator.last_latency_ms = None
        generator.last_latency_ms = None
        started = time.perf_counter()
        try:
            execution = service.answer(intent["question_vi"], "vi")
            response = execution.response.model_dump(mode="json")
            row: dict[str, Any] = {
                "schema_version": "multilingual_runtime_v1_m3_output_v1",
                "intent_id": intent["intent_id"],
                "runtime_status": "passed",
                "original_query": response["original_query"],
                "retrieval_query": response["retrieval_query"],
                "answer_language": response["answer_language"],
                "decision": response["decision"],
                "answer": response["answer"],
                "supporting_chunk_ids": response["supporting_chunk_ids"],
                "citations": response["citations"],
                "top3_chunk_ids": execution.top3_chunk_ids,
                "index_run_id": execution.index_run_id,
                "reason": execution.reason,
                "raw_model_output": execution.raw_model_output,
                "normalized_output": execution.normalized_output,
                "normalization_applied": execution.normalization_applied,
                "normalization_reason": execution.normalization_reason,
                "translation_prompt_eval_count": execution.translation_prompt_eval_count,
                "translation_eval_count": execution.translation_eval_count,
                "generation_prompt_eval_count": execution.prompt_eval_count,
                "generation_eval_count": execution.eval_count,
            }
        except Exception as error:  # One failed public execution is evaluation data; never retry.
            row = {
                "schema_version": "multilingual_runtime_v1_m3_output_v1",
                "intent_id": intent["intent_id"],
                "runtime_status": "failed",
                "original_query": intent["question_vi"],
                "retrieval_query": None,
                "answer_language": "vi",
                "decision": None,
                "answer": None,
                "supporting_chunk_ids": [],
                "citations": [],
                "top3_chunk_ids": [],
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        row["execution_attempt_id"] = EXECUTION_ATTEMPT_ID
        row["translation_call_count"] = translator.call_count - translator_before
        row["generation_call_count"] = generator.call_count - generator_before
        row["translation_latency_ms"] = translator.last_latency_ms
        row["generation_latency_ms"] = generator.last_latency_ms
        row["total_latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        rows.append(row)
        write_atomic(RAW_OUTPUT, serialize_jsonl(rows))
        print(
            f"[{len(rows):02d}/{len(intents)}] {intent['intent_id']} "
            f"{row['runtime_status']} {row['total_latency_ms']:.1f}ms"
        )
        if row["runtime_status"] == "failed":
            print("Runtime failure recorded; stopping attempt without retry or result selection.")
            break
    return rows


def build_review_rows(
    outputs: list[dict[str, Any]], questions: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    chunks = {str(row["chunk_id"]): row for row in load_jsonl(GOLD_FILE)}
    rows: list[dict[str, Any]] = []
    output_by_id = {str(output["intent_id"]): output for output in outputs}
    ordered_ids = deterministic_intent_order(list(output_by_id), REVIEW_ORDER_SEED)
    for intent_id in ordered_ids:
        output = output_by_id[intent_id]
        top3 = [
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "excerpt": chunks[chunk_id]["chunk_text"],
            }
            for rank, chunk_id in enumerate(output.get("top3_chunk_ids", []), start=1)
        ]
        selected = set(output.get("supporting_chunk_ids", []))
        selected_citations = [row for row in top3 if row["chunk_id"] in selected]
        rows.append(
            {
                "intent_id": intent_id,
                "evaluation_scope": (
                    "excluded_frozen_ground_truth_ambiguity"
                    if intent_id in PRIMARY_EXCLUDED_IDS
                    else "primary"
                ),
                "question_vi": output["original_query"],
                "expected_answer_points_json": canonical_json(
                    questions[intent_id]["expected_answer_points"]
                ),
                "retrieval_query": output.get("retrieval_query") or "",
                "top3_evidence_json": canonical_json(top3),
                "decision": output.get("decision") or "",
                "answer": output.get("answer") or "",
                "selected_citations_json": canonical_json(selected_citations),
                "runtime_status": output["runtime_status"],
                "evidence_sufficiency": "",
                "decision_judgment": "",
                "answer_correctness": "",
                "answer_completeness": "",
                "groundedness": "",
                "citation_support_overall": "",
                "output_language": "",
                "failure_attribution": "",
                "reviewer_notes": "",
            }
        )
    return rows


def build_execution_manifest(
    prereg: dict[str, Any],
    outputs: list[dict[str, Any]],
    runtime_identity: dict[str, Any],
) -> dict[str, Any]:
    passed_count = sum(row["runtime_status"] == "passed" for row in outputs)
    failed_count = sum(row["runtime_status"] == "failed" for row in outputs)
    complete = len(outputs) == EXPECTED_INTENT_COUNT and failed_count == 0
    return {
        "schema_version": "multilingual_runtime_v1_m3_execution_manifest_v1",
        "milestone": "multilingual_runtime_v1_m3",
        "status": (
            "executed_awaiting_human_review" if complete else "executed_failed_runtime"
        ),
        "preregistration": {
            "file": str(PREREGISTRATION.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(PREREGISTRATION),
            "revision": prereg["preregistration_revision"],
        },
        "runtime_identity": runtime_identity,
        "execution": {
            "attempt_id": EXECUTION_ATTEMPT_ID,
            "intent_count": len(outputs),
            "expected_intent_count": EXPECTED_INTENT_COUNT,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "translation_call_count": sum(row["translation_call_count"] for row in outputs),
            "generation_call_count": sum(row["generation_call_count"] for row in outputs),
            "retry_count": 0,
        },
        "output_artifacts": [
            {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in (RAW_OUTPUT, REVIEW_WORKSHEET)
        ],
        "ground_truth_exposed_to_runtime_calls": False,
        "quality_metrics_computed": False,
        "validation_status": "passed" if complete else "failed_runtime_integrity",
    }


def write_aborted_attempt(error: BaseException) -> None:
    completed_rows = load_jsonl(RAW_OUTPUT) if RAW_OUTPUT.exists() else []
    artifact = {
        "schema_version": "multilingual_runtime_v1_m3_attempt_failure_v1",
        "milestone": "multilingual_runtime_v1_m3",
        "status": "aborted_incomplete",
        "attempt_id": EXECUTION_ATTEMPT_ID,
        "completed_record_count": len(completed_rows),
        "expected_record_count": EXPECTED_INTENT_COUNT,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "partial_output": (
            {
                "file": str(RAW_OUTPUT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(RAW_OUTPUT),
            }
            if RAW_OUTPUT.exists()
            else None
        ),
        "quality_metrics_computed": False,
        "rerun_policy": "A new attempt ID and explicit user approval are required; this attempt must be retained.",
    }
    write_atomic(
        ATTEMPT_FAILURE,
        (json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the locked protocol and matched English baseline without loading models or calling Ollama.",
    )
    args = parser.parse_args()

    prereg, intents, questions = verify_preregistration()
    print(f"Pre-registration verified: {sha256_file(PREREGISTRATION)}")
    print(f"Frozen inputs verified: {len(prereg['frozen_inputs_sha256'])}")
    print(
        "Matched English baseline reproduced: "
        + canonical_json(prereg["frozen_english_matched_baseline"])
    )
    if args.verify_only:
        print("verify-only: no encoder load and no Ollama call was made.")
        return

    ensure_no_existing_results()
    search_service = DenseSearchService.load()
    base_translator = build_default_translation_provider()
    base_generator = build_default_provider()
    translator_runtime = base_translator.generator.verify_runtime()
    generator_runtime = base_generator.verify_runtime()
    translator = TimedTranslator(base_translator)
    generator = TimedGenerator(base_generator)

    try:
        outputs = execute_runtime(intents, search_service, translator, generator)
    except BaseException as error:
        write_aborted_attempt(error)
        raise
    review_rows = build_review_rows(outputs, questions)
    write_atomic(REVIEW_WORKSHEET, serialize_csv(review_rows))
    runtime_identity = {
        "translator": translator_runtime,
        "generator": generator_runtime,
        "retrieval_method": "dense_baseline_v1",
        "top_k": 3,
    }
    manifest = build_execution_manifest(prereg, outputs, runtime_identity)
    write_atomic(
        EXECUTION_MANIFEST,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
