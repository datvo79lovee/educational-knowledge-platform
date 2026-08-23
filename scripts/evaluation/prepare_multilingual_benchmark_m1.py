"""Build the Phase 9 M1 bilingual benchmark candidate without running retrieval."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_QUESTIONS = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
SOURCE_BENCHMARK_MANIFEST = PROJECT_ROOT / "evaluation/mit_60001/benchmark_manifest.json"
SILVER_FILE = PROJECT_ROOT / "data/silver/mit_60001/transcripts_clean.jsonl"
GOLD_FILE = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
TRANSLATION_LOG = PROJECT_ROOT / "evaluation/mit_60001/multilingual/translation_generation_v1.jsonl"
REVISION_LOG = PROJECT_ROOT / "evaluation/mit_60001/multilingual/translation_revision_log_v1.jsonl"
PAIRED_ARTIFACT = PROJECT_ROOT / "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl"
REVIEW_FILE = PROJECT_ROOT / "evaluation/review/multilingual/mit_60001_multilingual_m1_human_review.csv"
REVIEW_SOURCE_FILE = PROJECT_ROOT / "evaluation/review/multilingual/mit_60001_multilingual_m1_human_review_reviewed_by_user.csv"
MANIFEST_FILE = PROJECT_ROOT / "evaluation/mit_60001/multilingual/m1_manifest.json"
PAIRED_SCHEMA = PROJECT_ROOT / "schemas/multilingual_paired_intent_v1.schema.json"
MANIFEST_SCHEMA = PROJECT_ROOT / "schemas/multilingual_benchmark_manifest_v1.schema.json"
BOUNDARY_TOLERANCE = 1e-6

TRANSLATION_SYSTEM_PROMPT = (
    "Translate the Vietnamese question into literal, natural English. Preserve semantic intent and "
    "technical terms. Do not add, remove, explain, or answer anything. Return only the English question."
)
TRANSLATION_INPUT_FIELDS = ["question_vi"]
TRANSLATION_FORBIDDEN_FIELDS = [
    "question_en",
    "ground_truth_ranges",
    "expected_answer_points",
    "relevant_chunk_ids",
    "retrieved_evidence",
    "answer_labels",
]

SELECTED_INTENTS = {
    "mit60001-q-001": "multi_point",
    "mit60001-q-002": "procedure",
    "mit60001-q-003": "how",
    "mit60001-q-004": "comparison",
    "mit60001-q-005": "why",
    "mit60001-q-006": "how",
    "mit60001-q-008": "why",
    "mit60001-q-010": "comparison",
    "mit60001-q-014": "comparison",
    "mit60001-q-016": "what",
    "mit60001-q-020": "procedure",
    "mit60001-q-021": "concept_relationship",
    "mit60001-q-022": "why",
    "mit60001-q-023": "concept_relationship",
    "mit60001-q-025": "concept_relationship",
    "mit60001-q-029": "how",
    "mit60001-q-033": "multi_point",
    "mit60001-q-034": "concept_relationship",
    "mit60001-q-037": "comparison",
    "mit60001-q-039": "comparison",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def jsonl_bytes(rows: list[dict]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def review_csv_bytes(rows: list[dict]) -> bytes:
    fields = [
        "intent_id",
        "question_en",
        "question_vi",
        "literal_en",
        "review_status",
        "reviewer",
        "reviewed_at",
        "review_notes",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({field: row[field] for field in fields} for row in rows)
    return buffer.getvalue().encode("utf-8-sig")


def load_existing_reviews() -> dict[str, dict]:
    if not REVIEW_FILE.exists():
        return {}
    with REVIEW_FILE.open(encoding="utf-8-sig", newline="") as handle:
        return {row["intent_id"]: row for row in csv.DictReader(handle)}


def resolve_source_segment_ranges(question: dict, silver_by_video: dict[str, dict]) -> list[dict]:
    resolved = []
    for range_index, ground_truth in enumerate(question["relevant_time_ranges"], start=1):
        segments = silver_by_video[ground_truth["video_id"]]["segments"]
        starts = [
            segment["segment_index"]
            for segment in segments
            if abs(segment["start_second"] - ground_truth["start_second"]) < BOUNDARY_TOLERANCE
        ]
        ends = [
            segment["segment_index"]
            for segment in segments
            if abs(segment["start_second"] + segment["duration_second"] - ground_truth["end_second"])
            < BOUNDARY_TOLERANCE
        ]
        if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
            raise ValueError(f"Ground Truth boundary mapping failed: {question['question_id']} range {range_index}")
        resolved.append(
            {
                "range_index": range_index,
                "video_id": ground_truth["video_id"],
                "source_segment_start_index": starts[0],
                "source_segment_end_index": ends[0],
            }
        )
    return resolved


def relevant_chunk_ids(question: dict, silver_by_video: dict[str, dict], gold_rows: list[dict]) -> list[str]:
    ranges = resolve_source_segment_ranges(question, silver_by_video)
    ids = []
    covered_ranges = set()
    for chunk in gold_rows:
        for ground_truth in ranges:
            if (
                chunk["video_id"] == ground_truth["video_id"]
                and chunk["source_segment_start_index"] <= ground_truth["source_segment_end_index"]
                and chunk["source_segment_end_index"] >= ground_truth["source_segment_start_index"]
            ):
                ids.append(chunk["chunk_id"])
                covered_ranges.add(ground_truth["range_index"])
                break
    if covered_ranges != {item["range_index"] for item in ranges}:
        raise ValueError(f"Not all Ground Truth ranges map to canonical Gold: {question['question_id']}")
    return list(dict.fromkeys(ids))


def main() -> None:
    source_manifest = json.loads(SOURCE_BENCHMARK_MANIFEST.read_text(encoding="utf-8"))
    if source_manifest["input_sha256"]["evaluation_questions"] != sha256_file(SOURCE_QUESTIONS):
        raise ValueError("Canonical source benchmark hash mismatch")

    source_rows = {row["question_id"]: row for row in load_jsonl(SOURCE_QUESTIONS)}
    if set(SELECTED_INTENTS) - set(source_rows):
        raise ValueError("Selected question ID is absent from the canonical benchmark")
    for question_id in SELECTED_INTENTS:
        source = source_rows[question_id]
        if not source["answerable"] or source["review_status"] != "approved":
            raise ValueError(f"Selected intent is not canonical approved-answerable: {question_id}")

    translations = load_jsonl(TRANSLATION_LOG)
    allowed_translation_fields = {"intent_id", "question_vi", "literal_en", "translation_status"}
    if any(set(row) != allowed_translation_fields for row in translations):
        raise ValueError("Translation generation log contains unexpected fields; no-leakage contract failed")
    if set(TRANSLATION_FORBIDDEN_FIELDS) & allowed_translation_fields:
        raise ValueError("Translation input contract includes a forbidden field")
    translation_by_id = {row["intent_id"]: row for row in translations}
    if len(translations) != 20 or set(translation_by_id) != set(SELECTED_INTENTS):
        raise ValueError("Translation generation log must contain the exact 20 selected intents")

    silver_rows = load_jsonl(SILVER_FILE)
    gold_rows = load_jsonl(GOLD_FILE)
    if len(silver_rows) != 38 or len(gold_rows) != 861:
        raise ValueError("Canonical Silver/Gold counts changed")
    silver_by_video = {row["video_id"]: row for row in silver_rows}
    existing_reviews = load_existing_reviews()
    paired_rows = []
    for question_id, intent_type in SELECTED_INTENTS.items():
        source = source_rows[question_id]
        translation = translation_by_id[question_id]
        chunk_ids = relevant_chunk_ids(source, silver_by_video, gold_rows)
        prior = existing_reviews.get(question_id)
        if prior:
            for field, expected in {
                "question_en": source["question"],
                "question_vi": translation["question_vi"],
                "literal_en": translation["literal_en"],
            }.items():
                if prior[field] != expected:
                    raise ValueError(f"Stale human-review row after translation change: {question_id} {field}")
        review_status = prior["review_status"] if prior and prior["review_status"] else "Pending human review"
        reviewer = prior["reviewer"] or None if prior else None
        reviewed_at = prior["reviewed_at"] or None if prior else None
        review_notes = prior["review_notes"] if prior else ""
        paired_rows.append(
            {
                "schema_version": "multilingual_paired_intent_v1",
                "intent_id": question_id,
                "question_en": source["question"],
                "question_vi": translation["question_vi"],
                "literal_en": translation["literal_en"],
                "intent_type": intent_type,
                "source_category": source["category"],
                "ground_truth_ranges": source["relevant_time_ranges"],
                "relevant_chunk_ids": chunk_ids,
                "evidence_shape": "single_chunk" if len(chunk_ids) == 1 else "multiple_chunks",
                "translation_status": translation["translation_status"],
                "review_status": review_status,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "review_notes": review_notes,
            }
        )

    paired_schema = json.loads(PAIRED_SCHEMA.read_text(encoding="utf-8"))
    paired_validator = Draft202012Validator(paired_schema)
    for row in paired_rows:
        paired_validator.validate(row)

    write_atomic(PAIRED_ARTIFACT, jsonl_bytes(paired_rows))
    if not REVIEW_FILE.exists():
        write_atomic(REVIEW_FILE, review_csv_bytes(paired_rows))

    review_counts = Counter(row["review_status"] for row in paired_rows)
    unresolved = review_counts["Pending human review"] + review_counts["Semantic drift"]
    gate_passed = unresolved == 0 and sum(review_counts.values()) == 20
    manifest = {
        "$schema": "../../../schemas/multilingual_benchmark_manifest_v1.schema.json",
        "schema_version": "multilingual_benchmark_manifest_v1",
        "artifact_version": "mit_60001_multilingual_m1_v1",
        "status": "frozen" if gate_passed else "ready_for_human_review",
        "m1_gate_status": "passed" if gate_passed else "pending_human_review",
        "number_of_intents": len(paired_rows),
        "source": {
            "benchmark_questions_path": "evaluation/mit_60001/evaluation_questions.jsonl",
            "source_benchmark_hash": sha256_file(SOURCE_QUESTIONS),
            "benchmark_manifest_path": "evaluation/mit_60001/benchmark_manifest.json",
            "benchmark_manifest_sha256": sha256_file(SOURCE_BENCHMARK_MANIFEST),
            "canonical_gold_path": "data/gold/mit_60001/chunks.jsonl",
            "canonical_gold_sha256": sha256_file(GOLD_FILE),
            "silver_path": "data/silver/mit_60001/transcripts_clean.jsonl",
            "silver_sha256": sha256_file(SILVER_FILE),
            "ground_truth_policy": "copy canonical ranges unchanged and map relevant chunks by same-video source-segment interval intersection",
        },
        "selection": {
            "method": "purposeful coverage selection from canonical approved-answerable questions; no random sampling",
            "selected_question_ids": list(SELECTED_INTENTS),
            "intent_type_counts": dict(sorted(Counter(row["intent_type"] for row in paired_rows).items())),
            "evidence_shape_counts": dict(sorted(Counter(row["evidence_shape"] for row in paired_rows).items())),
            "single_ground_truth_range_count": sum(len(row["ground_truth_ranges"]) == 1 for row in paired_rows),
            "multiple_ground_truth_ranges_count": sum(len(row["ground_truth_ranges"]) > 1 for row in paired_rows),
        },
        "translation": {
            "translation_method": "ollama_local_literal_translation",
            "question_vi_authoring_method": "codex_draft_from_canonical_english_pending_human_review",
            "translation_input_fields": TRANSLATION_INPUT_FIELDS,
            "forbidden_input_fields": TRANSLATION_FORBIDDEN_FIELDS,
            "provider": "Ollama local",
            "provider_version": "0.32.15",
            "model": "llama3.2:3b",
            "model_digest": "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72",
            "system_prompt_sha256": sha256_text(TRANSLATION_SYSTEM_PROMPT),
            "generation_parameters": {"temperature": 0, "seed": 42, "num_predict": 128, "num_ctx": 4096},
        },
        "artifacts": {
            "paired_artifact": {"path": "evaluation/mit_60001/multilingual/paired_intents_v1.jsonl", "sha256": sha256_file(PAIRED_ARTIFACT)},
            "paired_schema": {"path": "schemas/multilingual_paired_intent_v1.schema.json", "sha256": sha256_file(PAIRED_SCHEMA)},
            "translation_generation_log": {"path": "evaluation/mit_60001/multilingual/translation_generation_v1.jsonl", "sha256": sha256_file(TRANSLATION_LOG)},
            "translation_revision_log": {"path": "evaluation/mit_60001/multilingual/translation_revision_log_v1.jsonl", "sha256": sha256_file(REVISION_LOG)},
            "human_review": {"path": "evaluation/review/multilingual/mit_60001_multilingual_m1_human_review.csv", "sha256": sha256_file(REVIEW_FILE)},
            "human_review_source": {"path": "evaluation/review/multilingual/mit_60001_multilingual_m1_human_review_reviewed_by_user.csv", "sha256": sha256_file(REVIEW_SOURCE_FILE)},
        },
        "review": {
            "allowed_labels": ["Equivalent", "Minor wording difference", "Semantic drift"],
            "completed_count": 20 - review_counts["Pending human review"],
            "pending_count": review_counts["Pending human review"],
            "semantic_drift_count": review_counts["Semantic drift"],
            "review_status_counts": dict(sorted(review_counts.items())),
            "reviewer_counts": dict(sorted(Counter(row["reviewer"] for row in paired_rows if row["reviewer"]).items())),
        },
        "validation_status": "passed",
    }
    Draft202012Validator(json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))).validate(manifest)
    write_atomic(MANIFEST_FILE, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"validation_status": "passed", "m1_gate_status": manifest["m1_gate_status"], "number_of_intents": 20, "review": manifest["review"], "selection": manifest["selection"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
