"""Build deterministic provider-independent evidence-review package.

Script gọi ``POST /search`` qua ASGI HTTP cho toàn bộ 40 câu approved. Request
package không chứa Ground Truth; calibration reference được lưu riêng để không
làm rò nhãn vào reviewer runtime.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.search_api.app import app


EVALUATION_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
BASELINE_FILE = PROJECT_ROOT / "reports/09_embedding/production_index_retrieval_results.csv"
SEARCH_API_MANIFEST_FILE = PROJECT_ROOT / "reports/12_search_api/search_api_validation_manifest.json"
RERANKING_NOTES_FILE = PROJECT_ROOT / "reports/11_reranking/README.md"
CONTRACT_FILE = PROJECT_ROOT / "docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md"
REQUEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json"
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_package_manifest_v1.schema.json"

REQUEST_PACKAGE = Path(
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
CALIBRATION_FILE = Path(
    "evaluation/review/evidence_accept_reject/evidence_review_calibration_v1.csv"
)
VALIDATION_FILE = Path("reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_validation.csv")
MANIFEST_FILE = Path("reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_manifest.json")

RETRIEVAL_METHOD = "dense_baseline_v1"
INDEX_RUN_ID = "mit60001_index_558e4d6e873847dd"
SEARCH_API_VALIDATION_RUN_ID = "mit60001_search_api_35767a6f304c4dc3"
TOP_K = 3
AUDIT_FLAGGED_QUESTIONS = {"mit60001-q-023", "mit60001-q-041"}
EXPECTED_CALIBRATION_COUNTS = {
    "strong_accept": 16,
    "strong_reject": 12,
    "needs_human_review": 12,
}


def canonical_json(value: Any) -> str:
    """JSON ổn định dùng cho JSONL, manifest và run identity."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def serialize_jsonl(records: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(record) for record in records) + "\n").encode("utf-8")


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("Cannot serialize an empty CSV")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def retrieval_identity() -> dict[str, Any]:
    return {
        "retrieval_method": RETRIEVAL_METHOD,
        "index_run_id": INDEX_RUN_ID,
        "search_api_validation_run_id": SEARCH_API_VALIDATION_RUN_ID,
        "top_k": TOP_K,
    }


def validate_source_state(
    questions: list[dict[str, Any]],
    baseline_by_id: dict[str, dict[str, str]],
    search_manifest: dict[str, Any],
) -> None:
    approved = [record for record in questions if record.get("review_status") == "approved"]
    answerable = [record for record in approved if record.get("answerable") is True]
    out_of_scope = [record for record in approved if record.get("answerable") is False]
    if (len(approved), len(answerable), len(out_of_scope)) != (40, 35, 5):
        raise ValueError("Expected 40 approved questions: 35 answerable and 5 out-of-scope")
    if set(baseline_by_id) != {str(record["question_id"]) for record in answerable}:
        raise ValueError("Dense baseline must contain exactly the 35 answerable questions")
    expected_manifest = {
        "validation_status": "passed",
        "retrieval_method": RETRIEVAL_METHOD,
        "validation_run_id": SEARCH_API_VALIDATION_RUN_ID,
        "top_k": TOP_K,
        "approved_question_count": 40,
    }
    for field, expected in expected_manifest.items():
        if search_manifest.get(field) != expected:
            raise ValueError(f"Search API manifest mismatch for {field}: {search_manifest.get(field)!r}")
    reranking_notes = RERANKING_NOTES_FILE.read_text(encoding="utf-8")
    if not all(token in reranking_notes for token in ("q-023", "q-041", "under-credit")):
        raise ValueError("Reranking audit note no longer supports q-023/q-041 flags")


def calibration_row(
    question: dict[str, Any], baseline: dict[str, str] | None
) -> dict[str, Any]:
    question_id = str(question["question_id"])
    answerable = bool(question["answerable"])
    first_relevant_rank = ""
    chunks_to_full_coverage = ""
    credited_evidence_status = "not_applicable"
    audit_flag = ""

    if not answerable:
        calibration_class = "strong_reject"
        calibration_basis = "out_of_scope"
    else:
        if baseline is None:
            raise ValueError(f"Missing Dense baseline row for {question_id}")
        first_relevant_rank = int(baseline["first_relevant_rank"])
        chunks_to_full_coverage = int(baseline["chunks_to_full_coverage"])
        if chunks_to_full_coverage <= TOP_K:
            credited_evidence_status = "full_coverage_in_top3"
            calibration_class = "strong_accept"
            calibration_basis = "full_credited_ground_truth_coverage"
        elif first_relevant_rank <= TOP_K:
            credited_evidence_status = "partial_coverage_in_top3"
            calibration_class = "needs_human_review"
            calibration_basis = "partial_credited_ground_truth_coverage"
        elif question_id in AUDIT_FLAGGED_QUESTIONS:
            credited_evidence_status = "no_credited_evidence_in_top3"
            audit_flag = "possible_ground_truth_under_credit"
            calibration_class = "needs_human_review"
            calibration_basis = "reranking_human_audit_flag"
        else:
            credited_evidence_status = "no_credited_evidence_in_top3"
            calibration_class = "strong_reject"
            calibration_basis = "retrieval_miss_no_credited_evidence_in_top3"

    reference_decision = {
        "strong_accept": "accept",
        "strong_reject": "reject",
        "needs_human_review": "",
    }[calibration_class]

    return {
        "question_id": question_id,
        "question": question["question"],
        "answerable": answerable,
        "first_relevant_rank": first_relevant_rank,
        "chunks_to_full_coverage": chunks_to_full_coverage,
        "credited_evidence_status": credited_evidence_status,
        "calibration_class": calibration_class,
        "reference_decision": reference_decision,
        "calibration_basis": calibration_basis,
        "human_review_required": calibration_class == "needs_human_review",
        "audit_flag": audit_flag,
    }


async def build_records(
    questions: list[dict[str, Any]], request_validator: Draft202012Validator
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for question in questions:
                response = await client.post("/search", json={"query": question["question"]})
                if response.status_code != 200:
                    raise ValueError(
                        f"Search API returned {response.status_code} for {question['question_id']}"
                    )
                payload = response.json()
                if payload.get("retrieval_method") != RETRIEVAL_METHOD:
                    raise ValueError("Search API retrieval_method drift")
                if payload.get("index_run_id") != INDEX_RUN_ID:
                    raise ValueError("Search API index_run_id drift")
                candidates = payload.get("results", [])
                if len(candidates) != TOP_K:
                    raise ValueError(f"Expected Top 3 for {question['question_id']}")
                if [item.get("rank") for item in candidates] != [1, 2, 3]:
                    raise ValueError(f"Invalid rank sequence for {question['question_id']}")
                chunk_ids = [str(item.get("chunk_id")) for item in candidates]
                if len(set(chunk_ids)) != TOP_K:
                    raise ValueError(f"Duplicate chunk ID for {question['question_id']}")

                record = {
                    "schema_version": "evidence_review_request_v1",
                    "request_id": f"evidence-review-{question['question_id']}",
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "scope_version": question["scope_version"],
                    "retrieval_identity": retrieval_identity(),
                    "candidates": candidates,
                }
                errors = sorted(request_validator.iter_errors(record), key=lambda item: list(item.path))
                if errors:
                    raise ValueError(
                        f"Request schema failed for {question['question_id']}: {errors[0].message}"
                    )
                records.append(record)
    return records


async def build(output_root: Path) -> dict[str, Any]:
    questions = sorted(
        (
            record
            for record in load_jsonl(EVALUATION_FILE)
            if record.get("review_status") == "approved"
        ),
        key=lambda record: str(record["question_id"]),
    )
    baseline_by_id = {
        row["question_id"]: row for row in load_csv(BASELINE_FILE)
    }
    search_manifest = json.loads(SEARCH_API_MANIFEST_FILE.read_text(encoding="utf-8"))
    validate_source_state(questions, baseline_by_id, search_manifest)

    request_schema = json.loads(REQUEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(request_schema)
    Draft202012Validator.check_schema(response_schema)
    Draft202012Validator.check_schema(manifest_schema)

    request_records = await build_records(questions, Draft202012Validator(request_schema))
    calibration_rows = [
        calibration_row(question, baseline_by_id.get(str(question["question_id"])))
        for question in questions
    ]
    calibration_counts = Counter(row["calibration_class"] for row in calibration_rows)
    if dict(calibration_counts) != EXPECTED_CALIBRATION_COUNTS:
        raise ValueError(
            f"Calibration count mismatch: {dict(calibration_counts)} != {EXPECTED_CALIBRATION_COUNTS}"
        )
    fabricated_review_labels = sum(
        row["calibration_class"] == "needs_human_review" and row["reference_decision"] != ""
        for row in calibration_rows
    )
    if fabricated_review_labels:
        raise ValueError("needs_human_review rows must not receive accept/reject labels")

    request_bytes = serialize_jsonl(request_records)
    calibration_bytes = serialize_csv(calibration_rows)

    input_files = {
        "evaluation": EVALUATION_FILE,
        "dense_baseline": BASELINE_FILE,
        "search_api_validation_manifest": SEARCH_API_MANIFEST_FILE,
        "search_api_application": PROJECT_ROOT / "src/search_api/app.py",
        "search_api_contract": PROJECT_ROOT / "src/search_api/contracts.py",
        "search_api_service": PROJECT_ROOT / "src/search_api/service.py",
        "evidence_review_contract": CONTRACT_FILE,
        "request_schema": REQUEST_SCHEMA_FILE,
        "response_schema": RESPONSE_SCHEMA_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "reranking_human_notes": RERANKING_NOTES_FILE,
        "builder": Path(__file__).resolve(),
    }
    input_sha256 = {
        label: sha256_file(path) for label, path in sorted(input_files.items())
    }
    package_run_id = "mit60001_evidence_review_" + sha256_bytes(
        canonical_json(input_sha256).encode("utf-8")
    )[:16]

    validation_rows = [
        {
            "package_run_id": package_run_id,
            "question_count": len(request_records),
            "unique_question_count": len({record["question_id"] for record in request_records}),
            "request_schema_pass_count": len(request_records),
            "top3_count_pass_count": sum(len(record["candidates"]) == TOP_K for record in request_records),
            "strong_accept_count": calibration_counts["strong_accept"],
            "strong_reject_count": calibration_counts["strong_reject"],
            "needs_human_review_count": calibration_counts["needs_human_review"],
            "unlabeled_human_review_count": sum(
                row["calibration_class"] == "needs_human_review"
                and row["reference_decision"] == ""
                for row in calibration_rows
            ),
            "fabricated_human_review_label_count": fabricated_review_labels,
            "llm_call_count": 0,
            "validation_status": "passed",
        }
    ]
    validation_bytes = serialize_csv(validation_rows)

    output_payloads = {
        REQUEST_PACKAGE: request_bytes,
        CALIBRATION_FILE: calibration_bytes,
        VALIDATION_FILE: validation_bytes,
    }
    output_artifacts = [
        {"file": path.as_posix(), "sha256": sha256_bytes(content)}
        for path, content in output_payloads.items()
    ]
    manifest = {
        "$schema": "../../schemas/evidence_review_package_manifest_v1.schema.json",
        "schema_version": "evidence_review_package_manifest_v1",
        "package_run_id": package_run_id,
        "generation_mode": "search_api_asgi_http",
        "retrieval_identity": retrieval_identity(),
        "question_count": 40,
        "answerable_question_count": 35,
        "out_of_scope_question_count": 5,
        "calibration_counts": dict(calibration_counts),
        "input_sha256": input_sha256,
        "output_artifacts": output_artifacts,
        "validation_status": "passed",
    }
    manifest_errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if manifest_errors:
        raise ValueError(f"Manifest schema failed: {manifest_errors[0].message}")

    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)
    write_atomic(
        output_root / MANIFEST_FILE,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Root nhận evaluation/ và reports/; mặc định là repository root.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = asyncio.run(build(args.output_root.resolve()))
    print(canonical_json({
        "package_run_id": manifest["package_run_id"],
        "question_count": manifest["question_count"],
        "calibration_counts": manifest["calibration_counts"],
        "validation_status": manifest["validation_status"],
    }))


if __name__ == "__main__":
    main()
