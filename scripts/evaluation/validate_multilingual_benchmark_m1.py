"""Validate Phase 9 M1 paired benchmark, hashes, Ground Truth reuse, and leakage contract."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from prepare_multilingual_benchmark_m1 import (
    GOLD_FILE,
    MANIFEST_FILE,
    MANIFEST_SCHEMA,
    PAIRED_ARTIFACT,
    PAIRED_SCHEMA,
    REVIEW_FILE,
    REVIEW_SOURCE_FILE,
    REVISION_LOG,
    SELECTED_INTENTS,
    SILVER_FILE,
    SOURCE_BENCHMARK_MANIFEST,
    SOURCE_QUESTIONS,
    TRANSLATION_FORBIDDEN_FIELDS,
    TRANSLATION_INPUT_FIELDS,
    TRANSLATION_LOG,
    load_jsonl,
    relevant_chunk_ids,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    Draft202012Validator(json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))).validate(manifest)

    artifact_paths = {
        "paired_artifact": PAIRED_ARTIFACT,
        "paired_schema": PAIRED_SCHEMA,
        "translation_generation_log": TRANSLATION_LOG,
        "translation_revision_log": REVISION_LOG,
        "human_review": REVIEW_FILE,
        "human_review_source": REVIEW_SOURCE_FILE,
    }
    for name, path in artifact_paths.items():
        if manifest["artifacts"][name]["sha256"] != sha256_file(path):
            raise ValueError(f"Manifest hash mismatch: {name}")
    if manifest["source"]["source_benchmark_hash"] != sha256_file(SOURCE_QUESTIONS):
        raise ValueError("Source benchmark hash mismatch")
    if manifest["source"]["benchmark_manifest_sha256"] != sha256_file(SOURCE_BENCHMARK_MANIFEST):
        raise ValueError("Source benchmark manifest hash mismatch")
    if manifest["source"]["canonical_gold_sha256"] != sha256_file(GOLD_FILE):
        raise ValueError("Canonical Gold hash mismatch")
    if manifest["source"]["silver_sha256"] != sha256_file(SILVER_FILE):
        raise ValueError("Canonical Silver hash mismatch")

    translations = load_jsonl(TRANSLATION_LOG)
    allowed_translation_fields = {"intent_id", "question_vi", "literal_en", "translation_status"}
    if any(set(row) != allowed_translation_fields for row in translations):
        raise ValueError("No-leakage contract failed: translation log field set")
    if TRANSLATION_INPUT_FIELDS != ["question_vi"]:
        raise ValueError("No-leakage contract failed: translator input is not question_vi-only")
    if set(TRANSLATION_FORBIDDEN_FIELDS) & allowed_translation_fields:
        raise ValueError("No-leakage contract failed: forbidden data appears in translator log")

    source_by_id = {row["question_id"]: row for row in load_jsonl(SOURCE_QUESTIONS)}
    translation_by_id = {row["intent_id"]: row for row in translations}
    paired_rows = load_jsonl(PAIRED_ARTIFACT)
    if len(paired_rows) != 20 or {row["intent_id"] for row in paired_rows} != set(SELECTED_INTENTS):
        raise ValueError("Paired artifact does not contain the exact selected 20 intents")
    validator = Draft202012Validator(json.loads(PAIRED_SCHEMA.read_text(encoding="utf-8")))
    silver_by_video = {row["video_id"]: row for row in load_jsonl(SILVER_FILE)}
    gold_rows = load_jsonl(GOLD_FILE)
    for row in paired_rows:
        validator.validate(row)
        source = source_by_id[row["intent_id"]]
        translation = translation_by_id[row["intent_id"]]
        if row["question_en"] != source["question"]:
            raise ValueError(f"Canonical English question changed: {row['intent_id']}")
        if row["ground_truth_ranges"] != source["relevant_time_ranges"]:
            raise ValueError(f"Canonical Ground Truth changed: {row['intent_id']}")
        if row["relevant_chunk_ids"] != relevant_chunk_ids(source, silver_by_video, gold_rows):
            raise ValueError(f"Relevant chunk mapping changed: {row['intent_id']}")
        if row["question_vi"] != translation["question_vi"] or row["literal_en"] != translation["literal_en"]:
            raise ValueError(f"Translation log mismatch: {row['intent_id']}")

    with REVIEW_FILE.open(encoding="utf-8-sig", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    with REVIEW_SOURCE_FILE.open(encoding="utf-8-sig", newline="") as handle:
        review_source_rows = list(csv.DictReader(handle))
    if len(review_rows) != 20 or {row["intent_id"] for row in review_rows} != set(SELECTED_INTENTS):
        raise ValueError("Human-review file does not contain the exact selected 20 intents")
    if review_rows != review_source_rows:
        raise ValueError("Canonical human review does not match the user-reviewed source")

    pending = sum(row["review_status"] == "Pending human review" for row in paired_rows)
    drift = sum(row["review_status"] == "Semantic drift" for row in paired_rows)
    expected_gate = "passed" if pending == 0 and drift == 0 else "pending_human_review"
    if manifest["m1_gate_status"] != expected_gate:
        raise ValueError("M1 gate status does not match human-review state")
    print(json.dumps({"validation_status": "passed", "m1_gate_status": expected_gate, "number_of_intents": len(paired_rows), "pending_human_review": pending, "semantic_drift": drift, "ground_truth_leakage": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
