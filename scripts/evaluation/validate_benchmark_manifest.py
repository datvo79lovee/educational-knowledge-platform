"""Validate the compact canonical MIT 6.0001 benchmark manifest."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
MANIFEST_FILE = PROJECT_ROOT / "evaluation/mit_60001/benchmark_manifest.json"
QUESTION_SCHEMA_FILE = PROJECT_ROOT / "schemas/chunking_evaluation_question_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/benchmark_manifest_v1.schema.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    questions = [
        json.loads(line)
        for line in QUESTIONS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    question_schema = json.loads(QUESTION_SCHEMA_FILE.read_text(encoding="utf-8"))
    question_validator = Draft202012Validator(question_schema)
    for row in questions:
        question_validator.validate(row)

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator(manifest_schema).validate(manifest)

    actual = {
        "question_count": len(questions),
        "answerable_count": sum(row["answerable"] for row in questions),
        "out_of_scope_count": sum(not row["answerable"] for row in questions),
        "ground_truth_range_count": sum(len(row["relevant_time_ranges"]) for row in questions),
        "question_schema_version": next(iter({row["schema_version"] for row in questions})),
        "all_questions_approved": all(row["review_status"] == "approved" for row in questions),
        "reviewer_batches": dict(sorted(Counter(row["reviewer"] for row in questions).items())),
    }
    expected = manifest["benchmark"]
    for key in expected:
        if actual[key] != expected[key]:
            raise ValueError(f"Benchmark manifest mismatch: {key}")
    if actual["reviewer_batches"] != manifest["ground_truth_provenance"]["reviewer_batches"]:
        raise ValueError("Benchmark manifest mismatch: reviewer_batches")
    if manifest["input_sha256"]["evaluation_questions"] != sha256_file(QUESTIONS_FILE):
        raise ValueError("Benchmark manifest hash mismatch: evaluation_questions")
    if manifest["input_sha256"]["question_schema"] != sha256_file(QUESTION_SCHEMA_FILE):
        raise ValueError("Benchmark manifest hash mismatch: question_schema")

    print(json.dumps({"validation_status": "passed", **actual}, ensure_ascii=False))


if __name__ == "__main__":
    main()
