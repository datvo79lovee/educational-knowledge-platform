"""Validate M2B artifacts độc lập, không gọi model và không đọc Ground Truth."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
RESPONSE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)
VALIDATION_FILE = PROJECT_ROOT / (
    "reports/14_evidence_review_runtime/evidence_review_runtime_validation.csv"
)
MANIFEST_FILE = PROJECT_ROOT / (
    "reports/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
)
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = (
    PROJECT_ROOT / "schemas/evidence_review_runtime_manifest_v1.schema.json"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    requests = load_jsonl(REQUEST_FILE)
    responses = load_jsonl(RESPONSE_FILE)
    request_by_id = {item["question_id"]: item for item in requests}
    response_by_id = {item["question_id"]: item for item in responses}
    if len(requests) != 40 or len(request_by_id) != 40:
        raise ValueError("Request package must contain 40 unique questions")
    if len(responses) != 40 or len(response_by_id) != 40:
        raise ValueError("Runtime output must contain 40 unique questions")
    if set(request_by_id) != set(response_by_id):
        raise ValueError("Runtime output question IDs do not match request package")

    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    response_validator = Draft202012Validator(response_schema)
    for question_id, response in response_by_id.items():
        errors = sorted(
            response_validator.iter_errors(response), key=lambda item: list(item.path)
        )
        if errors:
            raise ValueError(f"Response schema failed for {question_id}: {errors[0].message}")
        request = request_by_id[question_id]
        expected_ids = [candidate["chunk_id"] for candidate in request["candidates"]]
        if response["top3_chunk_ids"] != expected_ids:
            raise ValueError(f"Top 3 identity drift for {question_id}")
        if response["retrieval_identity"] != request["retrieval_identity"]:
            raise ValueError(f"Retrieval identity drift for {question_id}")
        if not set(response["supporting_chunk_ids"]).issubset(expected_ids):
            raise ValueError(f"Outside-Top-3 supporting ID for {question_id}")

    with VALIDATION_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        validation_rows = list(csv.DictReader(handle))
    if len(validation_rows) != 40:
        raise ValueError("Runtime validation CSV must contain 40 rows")
    status_fields = (
        "json_parse_status",
        "decision_contract_status",
        "top3_subset_status",
        "response_schema_status",
        "runtime_status",
    )
    if any(row[field] != "passed" for row in validation_rows for field in status_fields):
        raise ValueError("Runtime validation CSV contains a failed status")

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if manifest_errors:
        raise ValueError(f"Runtime manifest schema failed: {manifest_errors[0].message}")
    artifact_paths = {
        str(RESPONSE_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/"): RESPONSE_FILE,
        str(VALIDATION_FILE.relative_to(PROJECT_ROOT)).replace("\\", "/"): VALIDATION_FILE,
    }
    for artifact in manifest["output_artifacts"]:
        actual_hash = sha256_file(artifact_paths[artifact["file"]])
        if actual_hash != artifact["sha256"]:
            raise ValueError(f"Artifact hash mismatch: {artifact['file']}")

    decisions = Counter(item["decision"] for item in responses)
    if decisions["accept"] != manifest["accept_count"]:
        raise ValueError("Manifest accept_count mismatch")
    if decisions["reject"] != manifest["reject_count"]:
        raise ValueError("Manifest reject_count mismatch")
    print(
        json.dumps(
            {
                "question_count": len(responses),
                "accept_count": decisions["accept"],
                "reject_count": decisions["reject"],
                "failure_count": 0,
                "validation_status": "passed",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()

