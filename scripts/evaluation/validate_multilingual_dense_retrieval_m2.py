"""Validate M2 retrieval outputs without calculating relevance/quality metrics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

from run_multilingual_dense_retrieval_m2 import (
    CANONICAL_RETRIEVAL_RESULTS,
    GOLD_FILE,
    INDEX_MANIFEST_FILE,
    M1_ARTIFACT,
    M1_MANIFEST,
    MANIFEST_SCHEMA,
    RESULT_SCHEMA,
    load_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/27_multilingual_dense_retrieval"
RESULTS_FILE = REPORT_DIR / "multilingual_dense_retrieval_results.jsonl"
MANIFEST_FILE = REPORT_DIR / "multilingual_dense_retrieval_manifest.json"
CROSS_PROCESS_FILE = REPORT_DIR / "multilingual_dense_retrieval_cross_process_validation.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))).validate(manifest)
    if manifest["m1"]["paired_artifact_sha256"] != sha256_file(M1_ARTIFACT):
        raise ValueError("M2 manifest M1 artifact hash mismatch")
    if manifest["m1"]["manifest_sha256"] != sha256_file(M1_MANIFEST):
        raise ValueError("M2 manifest M1 manifest hash mismatch")
    index_manifest = json.loads(INDEX_MANIFEST_FILE.read_text(encoding="utf-8"))
    for field in ("canonical_gold_sha256", "index_content_sha256", "embeddings_sha256", "metadata_sha256", "chunk_id_order_sha256"):
        if manifest["index"][field] != index_manifest[field]:
            raise ValueError(f"M2 canonical index field mismatch: {field}")
    if manifest["artifacts"]["results"]["sha256"] != sha256_file(RESULTS_FILE):
        raise ValueError("M2 result artifact hash mismatch")
    if manifest["artifacts"]["result_schema"]["sha256"] != sha256_file(RESULT_SCHEMA):
        raise ValueError("M2 result schema hash mismatch")

    paired_rows = load_jsonl(M1_ARTIFACT)
    paired_by_id = {row["intent_id"]: row for row in paired_rows}
    result_rows = load_jsonl(RESULTS_FILE)
    if len(result_rows) != 40:
        raise ValueError("M2 must contain exactly 40 retrieval records")
    result_validator = Draft202012Validator(json.loads(RESULT_SCHEMA.read_text(encoding="utf-8")))
    gold_ids = {row["chunk_id"] for row in load_jsonl(GOLD_FILE)}
    seen_keys = set()
    for row in result_rows:
        result_validator.validate(row)
        key = (row["intent_id"], row["query_variant"])
        if key in seen_keys:
            raise ValueError(f"Duplicate M2 branch: {key}")
        seen_keys.add(key)
        paired = paired_by_id[row["intent_id"]]
        expected_query = paired["question_en"] if row["query_variant"] == "en_canonical" else paired["literal_en"]
        if row["query_text"] != expected_query:
            raise ValueError(f"M2 query differs from frozen M1: {key}")
        results = row["results"]
        if [item["rank"] for item in results] != list(range(1, 862)):
            raise ValueError(f"Invalid M2 ranks: {key}")
        chunk_ids = [item["chunk_id"] for item in results]
        if len(set(chunk_ids)) != 861 or set(chunk_ids) != gold_ids:
            raise ValueError(f"M2 result does not rank every canonical chunk exactly once: {key}")
        scores = [item["score"] for item in results]
        if any(not math.isfinite(score) or score < -1 or score > 1 for score in scores):
            raise ValueError(f"Invalid M2 score: {key}")
        if any(left < right for left, right in zip(scores, scores[1:])):
            raise ValueError(f"M2 scores are not descending: {key}")

    expected_keys = {(intent_id, variant) for intent_id in paired_by_id for variant in ("en_canonical", "vi_literal_en")}
    if seen_keys != expected_keys:
        raise ValueError("M2 missing intent/branch")
    by_key = {(row["intent_id"], row["query_variant"]): row for row in result_rows}
    identical_ids = [row["intent_id"] for row in paired_rows if row["question_en"] == row["literal_en"]]
    if any(by_key[(intent_id, "en_canonical")]["results"] != by_key[(intent_id, "vi_literal_en")]["results"] for intent_id in identical_ids):
        raise ValueError("Identical query string equivalence failed")

    baseline_by_id = {row["question_id"]: row for row in load_csv(CANONICAL_RETRIEVAL_RESULTS)}
    for intent_id in paired_by_id:
        current = by_key[(intent_id, "en_canonical")]["results"][:10]
        baseline = baseline_by_id[intent_id]
        if [item["chunk_id"] for item in current] != json.loads(baseline["top_10_chunk_ids_json"]):
            raise ValueError(f"English branch IDs differ from canonical baseline: {intent_id}")
        expected_scores = json.loads(baseline["top_10_scores_json"])
        if max(abs(item["score"] - expected) for item, expected in zip(current, expected_scores, strict=True)) > 1e-6:
            raise ValueError(f"English branch scores differ from canonical baseline: {intent_id}")

    execution = manifest["execution"]
    if execution["translator_calls"] != 0 or execution["llm_calls"] != 0 or execution["generator_calls"] != 0:
        raise ValueError("Forbidden translator/LLM/generator call recorded in M2")
    if execution["quality_metrics_computed"] or execution["ground_truth_fields_used_for_retrieval"]:
        raise ValueError("M2 must not use Ground Truth or calculate quality metrics")
    cross = json.loads(CROSS_PROCESS_FILE.read_text(encoding="utf-8"))
    if cross["validation_status"] != "passed":
        raise ValueError("M2 cross-process validation did not pass")
    if cross["canonical_results_sha256"] != sha256_file(RESULTS_FILE) or cross["canonical_manifest_sha256"] != sha256_file(MANIFEST_FILE):
        raise ValueError("M2 cross-process report hash mismatch")
    print(
        json.dumps(
            {
                "validation_status": "passed",
                "retrieval_records": 40,
                "en_queries": 20,
                "literal_en_queries": 20,
                "retrieval_depth": 861,
                "missing_intents": 0,
                "duplicate_branches": 0,
                "invalid_chunk_ids": 0,
                "translator_calls": 0,
                "quality_metrics_computed": False,
                "identical_query_pairs": len(identical_ids),
                "identical_query_equivalent": len(identical_ids),
                "deterministic_rerun": "passed",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
