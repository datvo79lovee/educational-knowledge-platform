"""Multilingual Runtime V1 - M2: measure the shipped machine translator.

Phase 9 measured retrieval on human-approved ``literal_en``. The runtime translates
with a local model instead, so Phase 9 results do not transfer. This script runs the
pinned runtime translator over the frozen 20 paired intents, checks determinism, and
recomputes Dense retrieval metrics for all three branches with the frozen M3
``branch_metrics`` function.

The script enforces the pre-registered contract before it calls the model: frozen
inputs and runtime sources must match their pre-registered hashes. It evaluates gate
G2 and prediction P1 automatically. It never closes gate G1, which requires human
adjudication, and it never edits a frozen artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.evaluate_multilingual_retrieval_m3 import (  # noqa: E402
    branch_metrics,
    resolve_ranges,
)
from src.multilingual.translation import (  # noqa: E402
    TRANSLATION_NUM_PREDICT,
    TRANSLATION_PROMPT_VERSION,
    build_default_translation_provider,
)

REPORT_DIR = PROJECT_ROOT / "reports/30_multilingual_runtime_v1_m2"
PREREGISTRATION = REPORT_DIR / "m2_preregistration.json"
ATTEMPT_1_FAILURE = REPORT_DIR / "m2_execution_attempt_1_failure.json"
M1_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
M1_MANIFEST = PROJECT_ROOT / "evaluation/mit_60001/multilingual/m1_manifest.json"
FROZEN_RESULTS = (
    PROJECT_ROOT / "reports/27_multilingual_dense_retrieval/multilingual_dense_retrieval_results.jsonl"
)
INDEX_MANIFEST = PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json"
GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
SILVER_FILE = PROJECT_ROOT / "data/silver/mit_60001/transcripts_clean.jsonl"

MACHINE_BRANCH = "machine_literal_en"
FROZEN_LITERAL_BRANCH = "literal_en_frozen_human"
EN_BRANCH = "question_en"
FROZEN_VARIANT_BY_BRANCH = {EN_BRANCH: "en_canonical", FROZEN_LITERAL_BRANCH: "vi_literal_en"}
METRIC_NAMES = ("mrr", "recall_at_1", "recall_at_3", "recall_at_5", "full_evidence_at_3")
PREDICTION_INTENT = "mit60001-q-008"
BASELINE_TOLERANCE = 1e-9
EXECUTION_ATTEMPT = 2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    """Hash with CRLF collapsed to LF so the value is checkout independent."""

    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8", newline="\n")


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify_frozen_inputs(prereg: dict[str, Any]) -> None:
    """Refuse to run if any pre-registered evaluation input changed."""

    for relative_path, expected in prereg["frozen_inputs_sha256"].items():
        actual = sha256_file(PROJECT_ROOT / relative_path)
        if actual != expected:
            raise ValueError(f"Pre-registered input changed since pre-registration: {relative_path}")


def verify_runtime_sources(prereg: dict[str, Any]) -> None:
    """Refuse to run if the runtime under test changed after pre-registration."""

    expected_map = prereg["runtime_under_test"]["source_sha256_lf_normalized"]
    if not expected_map:
        raise ValueError("Pre-registration does not pin any runtime source")
    for relative_path, expected in expected_map.items():
        actual = sha256_file_lf(PROJECT_ROOT / relative_path)
        if actual != expected:
            raise ValueError(f"Runtime under test changed since pre-registration: {relative_path}")


def verify_silver_from_frozen_m1() -> None:
    """Verify the local-only Silver input through the already-frozen M1 manifest."""

    m1_manifest = json.loads(M1_MANIFEST.read_text(encoding="utf-8"))
    source = m1_manifest["source"]
    expected_path = str(SILVER_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if source["silver_path"] != expected_path:
        raise ValueError("Frozen M1 manifest points to a different Silver artifact")
    if sha256_file(SILVER_FILE) != source["silver_sha256"]:
        raise ValueError("Local Silver hash does not match the frozen M1 manifest")


def ensure_no_existing_result_artifacts() -> None:
    """Prevent an accidental overwrite or unregistered third execution attempt."""

    names = (
        "m2_machine_translations.jsonl",
        "m2_machine_retrieval_results.jsonl",
        "m2_adjudication_worksheet.csv",
        "m2_metrics.json",
        "m2_manifest.json",
    )
    existing = [name for name in names if (REPORT_DIR / name).exists()]
    if existing:
        raise FileExistsError("M2 result artifacts already exist: " + ", ".join(existing))


def translate_all(intents: list[dict[str, Any]], run_label: str) -> list[dict[str, Any]]:
    """One translator call per intent; the translator sees only the Vietnamese query."""

    provider = build_default_translation_provider()
    rows: list[dict[str, Any]] = []
    for intent in intents:
        started = time.perf_counter()
        result = provider.translate(intent["question_vi"])
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        eval_count = result.eval_count
        rows.append(
            {
                "execution_attempt": EXECUTION_ATTEMPT,
                "run": run_label,
                "intent_id": intent["intent_id"],
                "question_vi": intent["question_vi"],
                "machine_literal_en": result.literal_en,
                "prompt_eval_count": result.prompt_eval_count,
                "eval_count": eval_count,
                "reached_num_predict_cap": bool(
                    eval_count is not None and eval_count >= TRANSLATION_NUM_PREDICT
                ),
                "latency_ms": elapsed_ms,
            }
        )
        print(f"  [{run_label}] {intent['intent_id']} {elapsed_ms:9.1f}ms  {result.literal_en[:66]}")
    return rows


def rank_machine_queries(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Full 861-depth ranking with the canonical encoder and the locked tie-break."""

    index_manifest = json.loads(INDEX_MANIFEST.read_text(encoding="utf-8"))
    gold_rows = load_jsonl(GOLD_FILE)
    vectors = np.load(PROJECT_ROOT / index_manifest["embeddings_file"], allow_pickle=False)
    model = SentenceTransformer(
        index_manifest["model_repository"],
        revision=index_manifest["model_revision"],
        local_files_only=True,
        device="cpu",
    )
    actual_revision = getattr(model._first_module().auto_model.config, "_commit_hash", None)
    if actual_revision != index_manifest["model_revision"] or model.get_embedding_dimension() != 384:
        raise RuntimeError("M2 query encoder differs from the canonical index encoder")

    query_vectors = model.encode(
        [row["machine_literal_en"] for row in rows],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vectors = np.asarray(query_vectors, dtype=np.float32, order="C")
    if query_vectors.shape != (len(rows), 384) or not np.isfinite(query_vectors).all():
        raise RuntimeError("M2 query encoder returned invalid vectors")
    scores_matrix = query_vectors @ vectors.T

    rankings: list[dict[str, Any]] = []
    for query_index, row in enumerate(rows):
        scores = scores_matrix[query_index]
        ranked_indices = sorted(
            range(len(gold_rows)),
            key=lambda index: (-float(scores[index]), gold_rows[index]["chunk_id"]),
        )
        rankings.append(
            {
                "schema_version": "multilingual_retrieval_result_v1",
                "intent_id": row["intent_id"],
                "query_variant": MACHINE_BRANCH,
                "query_text": row["machine_literal_en"],
                "retrieval_depth": len(ranked_indices),
                "results": [
                    {
                        "rank": rank,
                        "chunk_id": gold_rows[index]["chunk_id"],
                        "score": round(float(scores[index]), 8),
                    }
                    for rank, index in enumerate(ranked_indices, start=1)
                ],
            }
        )
    return rankings, {gold["chunk_id"]: gold for gold in gold_rows}


def determinism_report(runs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Compare every later run against run A translation by translation."""

    by_intent = {row["intent_id"]: row for row in runs["A"]}
    report: dict[str, Any] = {"runs": len(runs), "compared_pairs": [], "all_runs_identical": True}
    for label, rows in runs.items():
        if label == "A":
            continue
        mismatches = [
            row["intent_id"]
            for row in rows
            if row["machine_literal_en"] != by_intent[row["intent_id"]]["machine_literal_en"]
        ]
        report["compared_pairs"].append(
            {"pair": f"A_vs_{label}", "mismatch_count": len(mismatches), "mismatched_intent_ids": mismatches}
        )
        report["all_runs_identical"] = report["all_runs_identical"] and not mismatches
    return report


def aggregate_branch(rows: list[dict[str, Any]]) -> dict[str, float]:
    count = len(rows)
    return {
        "mrr": round(sum(row["reciprocal_rank"] for row in rows) / count, 9),
        "recall_at_1": round(sum(row["recall_at_1"] for row in rows) / count, 9),
        "recall_at_3": round(sum(row["recall_at_3"] for row in rows) / count, 9),
        "recall_at_5": round(sum(row["recall_at_5"] for row in rows) / count, 9),
        "full_evidence_at_3": round(sum(row["full_evidence_at_3"] for row in rows) / count, 9),
    }


def prepare_frozen_evaluation(
    intents: list[dict[str, Any]],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    """Resolve canonical ranges and reproduce both frozen branches before model calls."""

    verify_silver_from_frozen_m1()
    gold_rows = load_jsonl(GOLD_FILE)
    silver_rows = load_jsonl(SILVER_FILE)
    frozen_rows = load_jsonl(FROZEN_RESULTS)
    if len(gold_rows) != 861 or len(silver_rows) != 38 or len(frozen_rows) != 40:
        raise ValueError("Frozen Gold/Silver/retrieval counts changed")
    chunk_by_id = {row["chunk_id"]: row for row in gold_rows}
    silver_by_video = {row["video_id"]: row for row in silver_rows}
    frozen_by_key = {(row["intent_id"], row["query_variant"]): row for row in frozen_rows}
    if len(frozen_by_key) != 40:
        raise ValueError("Frozen retrieval results contain duplicate intent/branch records")

    ranges_by_intent: dict[str, list[dict[str, Any]]] = {}
    branch_rows = {EN_BRANCH: [], FROZEN_LITERAL_BRANCH: []}
    for intent in intents:
        intent_id = intent["intent_id"]
        ranges = resolve_ranges(intent, silver_by_video)
        ranges_by_intent[intent_id] = ranges
        computed_relevant_ids = [
            chunk["chunk_id"]
            for chunk in gold_rows
            if any(
                chunk["video_id"] == item["video_id"]
                and chunk["source_segment_start_index"] <= item["source_segment_end_index"]
                and chunk["source_segment_end_index"] >= item["source_segment_start_index"]
                for item in ranges
            )
        ]
        if computed_relevant_ids != intent["relevant_chunk_ids"]:
            raise ValueError(f"M1 relevant chunk mapping changed: {intent_id}")
        for branch, variant in FROZEN_VARIANT_BY_BRANCH.items():
            ranking = frozen_by_key[(intent_id, variant)]
            branch_rows[branch].append(branch_metrics(ranking, chunk_by_id, ranges))
    return frozen_by_key, chunk_by_id, ranges_by_intent, branch_rows


def verify_baseline_reproduction(branch_table: dict[str, dict[str, float]], prereg: dict[str, Any]) -> None:
    """The two frozen branches must reproduce the pre-registered Phase 9 baseline."""

    baseline = prereg["frozen_baseline_from_phase9"]
    for branch in (EN_BRANCH, FROZEN_LITERAL_BRANCH):
        expected = baseline["en_canonical" if branch == EN_BRANCH else "literal_en_frozen_human"]
        for metric in METRIC_NAMES:
            if abs(branch_table[branch][metric] - expected[metric]) > BASELINE_TOLERANCE:
                raise ValueError(
                    f"Frozen branch {branch} did not reproduce the Phase 9 baseline for {metric}: "
                    f"expected {expected[metric]}, recomputed {branch_table[branch][metric]}"
                )


def evaluate_prediction(per_intent: list[dict[str, Any]], prereg: dict[str, Any]) -> dict[str, Any]:
    """Machine-checkable evaluation of pre-registered prediction P1."""

    prediction = prereg["preregistered_predictions"][0]
    max_delta = max(row["rank_delta_machine_minus_frozen"] for row in per_intent)
    min_overlap = min(row["top_3_overlap"] for row in per_intent)
    worst_delta_ids = sorted(
        row["intent_id"] for row in per_intent if row["rank_delta_machine_minus_frozen"] == max_delta
    )
    worst_overlap_ids = sorted(row["intent_id"] for row in per_intent if row["top_3_overlap"] == min_overlap)
    criterion_a = PREDICTION_INTENT in worst_delta_ids
    criterion_b = PREDICTION_INTENT in worst_overlap_ids
    return {
        "prediction_id": prediction["id"],
        "intent_id": PREDICTION_INTENT,
        "criterion_a_max_rank_delta": {
            "max_rank_delta": max_delta,
            "intent_ids_at_max": worst_delta_ids,
            "satisfied": criterion_a,
        },
        "criterion_b_min_top_3_overlap": {
            "min_top_3_overlap": min_overlap,
            "intent_ids_at_min": worst_overlap_ids,
            "satisfied": criterion_b,
        },
        "result": "PASS" if (criterion_a or criterion_b) else "FAIL",
    }


def write_adjudication_worksheet(path: Path, per_intent: list[dict[str, Any]]) -> None:
    """Human closes gate G1 here; identical strings are pre-labelled Equivalent."""

    fieldnames = [
        "intent_id",
        "question_vi",
        "frozen_literal_en",
        "machine_literal_en",
        "exact_string_match",
        "rank_delta_machine_minus_frozen",
        "top_3_overlap",
        "adjudication",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in per_intent:
            writer.writerow(
                {
                    "intent_id": row["intent_id"],
                    "question_vi": row["question_vi"],
                    "frozen_literal_en": row["frozen_literal_en"],
                    "machine_literal_en": row["machine_literal_en"],
                    "exact_string_match": row["exact_string_match"],
                    "rank_delta_machine_minus_frozen": row["rank_delta_machine_minus_frozen"],
                    "top_3_overlap": row["top_3_overlap"],
                    "adjudication": "Equivalent" if row["exact_string_match"] else "",
                    "reviewer_notes": "auto: identical to frozen literal_en" if row["exact_string_match"] else "",
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2, help="Translator runs for the determinism check.")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Check the pre-registered contract and exit without calling the translator.",
    )
    args = parser.parse_args()
    if args.runs < 1:
        raise ValueError("At least one translator run is required")

    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    if prereg["status"] != "preregistered_not_executed":
        raise ValueError("Pre-registration is not in the pre-execution state")
    verify_frozen_inputs(prereg)
    verify_runtime_sources(prereg)
    prereg_hash = sha256_file(PREREGISTRATION)
    print(f"Pre-registration revision {prereg['preregistration_revision']} verified: {prereg_hash}")
    print(f"Frozen inputs verified   : {len(prereg['frozen_inputs_sha256'])}")
    print(f"Runtime sources verified : {len(prereg['runtime_under_test']['source_sha256_lf_normalized'])}")
    intents = load_jsonl(M1_ARTIFACT)
    if len(intents) != 20:
        raise ValueError("Frozen paired artifact must contain exactly 20 intents")
    intent_by_id = {intent["intent_id"]: intent for intent in intents}
    frozen_by_key, frozen_chunk_by_id, ranges_by_intent, frozen_branch_rows = (
        prepare_frozen_evaluation(intents)
    )
    frozen_branch_table = {
        branch: aggregate_branch(rows) for branch, rows in frozen_branch_rows.items()
    }
    verify_baseline_reproduction(frozen_branch_table, prereg)
    print("Frozen branch baseline reproduction: PASS")
    if args.verify_only:
        print("verify-only: contract and analysis mapping hold; no translator call was made.")
        return

    ensure_no_existing_result_artifacts()
    if not ATTEMPT_1_FAILURE.exists():
        raise FileNotFoundError("Execution attempt 1 failure record is required before attempt 2")
    translations_path = REPORT_DIR / "m2_machine_translations.jsonl"

    runs: dict[str, list[dict[str, Any]]] = {}
    for run_index in range(args.runs):
        label = chr(ord("A") + run_index)
        print(f"Translator run {label}:")
        runs[label] = translate_all(intents, label)
        write_jsonl(
            translations_path,
            [row for completed_label in sorted(runs) for row in runs[completed_label]],
        )
    determinism = determinism_report(runs)

    rankings, chunk_by_id = rank_machine_queries(runs["A"])
    if set(chunk_by_id) != set(frozen_chunk_by_id):
        raise ValueError("Machine ranking Gold differs from frozen evaluation Gold")
    translation_by_id = {row["intent_id"]: row for row in runs["A"]}
    machine_by_id = {ranking["intent_id"]: ranking for ranking in rankings}

    branch_rows: dict[str, list[dict[str, Any]]] = {
        EN_BRANCH: list(frozen_branch_rows[EN_BRANCH]),
        FROZEN_LITERAL_BRANCH: list(frozen_branch_rows[FROZEN_LITERAL_BRANCH]),
        MACHINE_BRANCH: [],
    }
    per_intent: list[dict[str, Any]] = []
    for intent in intents:
        intent_id = intent["intent_id"]
        ranges = ranges_by_intent[intent_id]
        metrics_by_branch: dict[str, dict[str, Any]] = {}
        for branch, variant in FROZEN_VARIANT_BY_BRANCH.items():
            ranking = frozen_by_key[(intent_id, variant)]
            metrics_by_branch[branch] = branch_metrics(ranking, chunk_by_id, ranges)
        machine_ranking = machine_by_id[intent_id]
        metrics_by_branch[MACHINE_BRANCH] = branch_metrics(machine_ranking, chunk_by_id, ranges)
        branch_rows[MACHINE_BRANCH].append(metrics_by_branch[MACHINE_BRANCH])

        frozen_literal_ranking = frozen_by_key[(intent_id, "vi_literal_en")]
        machine_top3 = {item["chunk_id"] for item in machine_ranking["results"][:3]}
        frozen_top3 = {item["chunk_id"] for item in frozen_literal_ranking["results"][:3]}
        per_intent.append(
            {
                "intent_id": intent_id,
                "question_vi": intent["question_vi"],
                "frozen_literal_en": frozen_literal_ranking["query_text"],
                "machine_literal_en": machine_ranking["query_text"],
                "exact_string_match": frozen_literal_ranking["query_text"] == machine_ranking["query_text"],
                "en_first_relevant_rank": metrics_by_branch[EN_BRANCH]["first_relevant_rank"],
                "frozen_first_relevant_rank": metrics_by_branch[FROZEN_LITERAL_BRANCH]["first_relevant_rank"],
                "machine_first_relevant_rank": metrics_by_branch[MACHINE_BRANCH]["first_relevant_rank"],
                "rank_delta_machine_minus_frozen": (
                    metrics_by_branch[MACHINE_BRANCH]["first_relevant_rank"]
                    - metrics_by_branch[FROZEN_LITERAL_BRANCH]["first_relevant_rank"]
                ),
                "top_3_overlap": len(machine_top3 & frozen_top3),
                "reached_num_predict_cap": translation_by_id[intent_id]["reached_num_predict_cap"],
            }
        )

    branch_table = {branch: aggregate_branch(rows) for branch, rows in branch_rows.items()}
    verify_baseline_reproduction(branch_table, prereg)

    gate_g2 = next(item for item in prereg["primary_gate"]["conditions_all_must_hold"] if item["id"] == "G2")
    g2_minimum = gate_g2["absolute_minimum_required"]
    observed_recall_at_3 = branch_table[MACHINE_BRANCH]["recall_at_3"]
    g2_pass = observed_recall_at_3 >= g2_minimum
    prediction = evaluate_prediction(per_intent, prereg)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rankings_path = REPORT_DIR / "m2_machine_retrieval_results.jsonl"
    worksheet_path = REPORT_DIR / "m2_adjudication_worksheet.csv"
    metrics_path = REPORT_DIR / "m2_metrics.json"
    manifest_path = REPORT_DIR / "m2_manifest.json"

    write_jsonl(rankings_path, rankings)
    write_adjudication_worksheet(worksheet_path, per_intent)

    run_a = runs["A"]
    metrics = {
        "schema_version": "multilingual_runtime_v1_m2_metrics_v1",
        "preregistration_sha256": prereg_hash,
        "preregistration_revision": prereg["preregistration_revision"],
        "status": "awaiting_human_adjudication",
        "execution_attempt": EXECUTION_ATTEMPT,
        "translator": {
            "prompt_version": TRANSLATION_PROMPT_VERSION,
            "num_predict_cap_hits": sum(1 for row in run_a if row["reached_num_predict_cap"]),
        },
        "determinism": determinism,
        "branch_metrics": branch_table,
        "frozen_baseline_reproduced": True,
        "deltas_machine_minus_frozen_literal_en": {
            metric: round(branch_table[MACHINE_BRANCH][metric] - branch_table[FROZEN_LITERAL_BRANCH][metric], 9)
            for metric in METRIC_NAMES
        },
        "gate_G2_recall_at_3": {
            "minimum_required": g2_minimum,
            "observed": observed_recall_at_3,
            "result": "PASS" if g2_pass else "FAIL",
        },
        "gate_G1_semantic_drift": {
            "result": "PENDING_HUMAN_ADJUDICATION",
            "worksheet": str(worksheet_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "rows_needing_human_label": sum(1 for row in per_intent if not row["exact_string_match"]),
        },
        "prediction_P1": prediction,
        "exact_string_match_count": sum(1 for row in per_intent if row["exact_string_match"]),
        "mean_top_3_overlap_rate": round(
            sum(row["top_3_overlap"] for row in per_intent) / (3 * len(per_intent)), 9
        ),
        "latency_ms": {
            "mean": round(sum(row["latency_ms"] for row in run_a) / len(run_a), 3),
            "max": max(row["latency_ms"] for row in run_a),
        },
        "per_intent": per_intent,
    }
    write_json(metrics_path, metrics)

    manifest = {
        "schema_version": "multilingual_runtime_v1_m2_manifest_v1",
        "milestone": "multilingual_runtime_v1_m2",
        "status": "executed_awaiting_human_adjudication",
        "execution_attempt": EXECUTION_ATTEMPT,
        "preregistration": {
            "file": "reports/30_multilingual_runtime_v1_m2/m2_preregistration.json",
            "revision": prereg["preregistration_revision"],
            "sha256": prereg_hash,
        },
        "frozen_inputs_sha256": prereg["frozen_inputs_sha256"],
        "local_silver_ground_truth_mapping": {
            "file": str(SILVER_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(SILVER_FILE),
            "verified_against": "evaluation/mit_60001/multilingual/m1_manifest.json:source.silver_sha256",
        },
        "runtime_under_test_sha256_lf_normalized": prereg["runtime_under_test"]["source_sha256_lf_normalized"],
        "translator_identity": prereg["runtime_under_test"]["translator"],
        "analysis_code_sha256_lf_normalized": {
            "scripts/evaluation/run_multilingual_runtime_translation_v1_m2.py": sha256_file_lf(Path(__file__)),
            "scripts/evaluation/evaluate_multilingual_retrieval_m3.py": sha256_file_lf(
                PROJECT_ROOT / "scripts/evaluation/evaluate_multilingual_retrieval_m3.py"
            ),
        },
        "prior_failed_attempt": {
            "file": str(ATTEMPT_1_FAILURE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(ATTEMPT_1_FAILURE),
        },
        "determinism": determinism,
        "gate_results": {
            "G1": "PENDING_HUMAN_ADJUDICATION",
            "G2": "PASS" if g2_pass else "FAIL",
            "P1": prediction["result"],
        },
        "output_artifacts": [
            {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
            for path in (translations_path, rankings_path, worksheet_path, metrics_path)
        ],
        "validation_status": "passed",
    }
    write_json(manifest_path, manifest)

    summary = {key: value for key, value in metrics.items() if key != "per_intent"}
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
