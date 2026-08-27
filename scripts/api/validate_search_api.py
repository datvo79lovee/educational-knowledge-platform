"""Validate Dense Search API trên toàn bộ canonical evaluation set.

Runner gọi FastAPI qua ASGI HTTP, không gọi trực tiếp retrieval method. Không có
output mặc định: successful validation chỉ in manifest lên stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import httpx
import numpy as np
from jsonschema import Draft202012Validator

# Khi gọi bằng đường dẫn file, Python chỉ thêm ``scripts/api`` vào sys.path. Thêm
# repository root để runner dùng đúng package ``src.search_api`` trong workspace.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.search_api.app import app
from src.search_api.service import (
    CANONICAL_GOLD_FILE,
    EMBEDDINGS_FILE,
    INDEX_MANIFEST_FILE,
    METADATA_FILE,
    RETRIEVAL_DECISION_FILE,
    DenseSearchService,
    _load_jsonl,
    _sha256_file,
)


EVALUATION_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
BASELINE_FILE = (
    PROJECT_ROOT / "reports/09_embedding/production_index_retrieval_results.csv"
)
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/search_api_validation_manifest_v2.schema.json"
SCORE_TOLERANCE = 1e-6
REPEAT_COUNT = 2

ANSWERABLE_FILE = "search_api_answerable_validation.csv"
OUT_OF_SCOPE_FILE = "search_api_out_of_scope_validation.csv"
VIDEO_FILE = "search_api_video_validation.csv"
FAILURE_FILE = "search_api_failure_validation.csv"
CITATION_FILE = "search_api_citation_validation.csv"
MANIFEST_FILE = "search_api_validation_manifest.json"
OUTPUT_FILES = (
    ANSWERABLE_FILE,
    OUT_OF_SCOPE_FILE,
    VIDEO_FILE,
    FAILURE_FILE,
    CITATION_FILE,
)


def canonical_json(value: Any) -> str:
    """Serialize JSON ổn định để so response và tạo run identity."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
    """Serialize CSV UTF-8 BOM với field order lấy từ row đầu tiên."""

    if not rows:
        raise ValueError("Cannot serialize an empty validation table")
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


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def expected_video_catalog(metadata: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in metadata:
        grouped.setdefault(str(item["video_id"]), []).append(item)
    result: dict[str, dict[str, Any]] = {}
    for video_id, items in grouped.items():
        result[video_id] = {
            "video_id": video_id,
            "video_title": str(items[0]["video_title"]),
            "source_url": str(items[0]["source_url"]),
            "chunk_count": len(items),
            "start_second": min(float(item["start_second"]) for item in items),
            "end_second": max(float(item["end_second"]) for item in items),
        }
    return result


def startup_failure_rows() -> list[dict[str, Any]]:
    """Chứng minh các lỗi artifact quan trọng làm startup dừng trước khi phục vụ."""

    rows: list[dict[str, Any]] = []

    def check(case_id: str, expected_exception: type[Exception], action: Callable[[], None]) -> None:
        actual = "no_error"
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - artifact ghi chính xác exception runtime
            actual = type(exc).__name__
        rows.append(
            {
                "layer": "startup",
                "case_id": case_id,
                "expected_status_or_exception": expected_exception.__name__,
                "actual_status_or_exception": actual,
                "passed": actual == expected_exception.__name__,
            }
        )

    manifest = json.loads(
        (PROJECT_ROOT / INDEX_MANIFEST_FILE).read_text(encoding="utf-8")
    )
    chunks = _load_jsonl(PROJECT_ROOT / CANONICAL_GOLD_FILE)
    metadata = _load_jsonl(PROJECT_ROOT / METADATA_FILE)
    vectors = np.load(PROJECT_ROOT / EMBEDDINGS_FILE, allow_pickle=False)

    with tempfile.TemporaryDirectory(prefix="mit60001_api_missing_") as raw_dir:
        check(
            "missing_required_artifact",
            FileNotFoundError,
            lambda: DenseSearchService.load(Path(raw_dir)),
        )

    invalid_manifest = dict(manifest)
    invalid_manifest["model_revision"] = "wrong-revision"
    check(
        "manifest_contract_mismatch",
        ValueError,
        lambda: DenseSearchService._validate_manifest_contract(invalid_manifest),
    )

    with tempfile.TemporaryDirectory(prefix="mit60001_api_decision_") as raw_dir:
        decision_path = Path(raw_dir) / "decision.csv"
        decision_path.write_text(
            "retrieval_method,selection_status\nbm25_v1,selected\n",
            encoding="utf-8",
        )
        check(
            "retrieval_decision_mismatch",
            ValueError,
            lambda: DenseSearchService._validate_retrieval_decision(decision_path),
        )

    with tempfile.TemporaryDirectory(prefix="mit60001_api_hash_") as raw_dir:
        temp_root = Path(raw_dir)
        for relative_path in (
            INDEX_MANIFEST_FILE,
            RETRIEVAL_DECISION_FILE,
            CANONICAL_GOLD_FILE,
            EMBEDDINGS_FILE,
            METADATA_FILE,
        ):
            target = temp_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT_ROOT / relative_path, target)
        with (temp_root / CANONICAL_GOLD_FILE).open("ab") as handle:
            handle.write(b"\n")
        check(
            "canonical_gold_hash_mismatch",
            ValueError,
            lambda: DenseSearchService.load(temp_root),
        )

    check(
        "embedding_shape_mismatch",
        ValueError,
        lambda: DenseSearchService._validate_index_content(
            manifest, chunks, metadata, vectors[:-1]
        ),
    )

    non_normalized = vectors.copy()
    non_normalized[0] = 0
    check(
        "embedding_norm_mismatch",
        ValueError,
        lambda: DenseSearchService._validate_index_content(
            manifest, chunks, metadata, non_normalized
        ),
    )

    wrong_order = list(metadata)
    wrong_order[0], wrong_order[1] = wrong_order[1], wrong_order[0]
    check(
        "metadata_order_mismatch",
        ValueError,
        lambda: DenseSearchService._validate_index_content(
            manifest, chunks, wrong_order, vectors
        ),
    )
    return rows


async def http_validation() -> dict[str, list[dict[str, Any]]]:
    """Chạy full canonical set qua ASGI HTTP với application lifespan thật."""

    evaluation = _load_jsonl(EVALUATION_FILE)
    approved = sorted(
        [record for record in evaluation if record["review_status"] == "approved"],
        key=lambda record: record["question_id"],
    )
    answerable = [record for record in approved if record["answerable"]]
    out_of_scope = [record for record in approved if not record["answerable"]]
    if len(approved) != 40 or len(answerable) != 35 or len(out_of_scope) != 5:
        raise ValueError("Expected 40 approved questions: 35 answerable and 5 out-of-scope")

    baseline = {row["question_id"]: row for row in load_csv(BASELINE_FILE)}
    if set(baseline) != {record["question_id"] for record in answerable}:
        raise ValueError("Locked Dense baseline does not match 35 answerable questions")

    chunks = _load_jsonl(PROJECT_ROOT / CANONICAL_GOLD_FILE)
    metadata = _load_jsonl(PROJECT_ROOT / METADATA_FILE)
    chunk_by_id = {record["chunk_id"]: record for record in chunks}
    metadata_by_id = {record["chunk_id"]: record for record in metadata}
    video_catalog = expected_video_catalog(metadata)

    answerable_rows: list[dict[str, Any]] = []
    out_of_scope_rows: list[dict[str, Any]] = []
    video_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    citation_rows: list[dict[str, Any]] = []

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://search-api.test",
        ) as client:
            for question in approved:
                responses = [
                    await client.post("/search", json={"query": question["question"]})
                    for _ in range(REPEAT_COUNT)
                ]
                status_match = all(response.status_code == 200 for response in responses)
                bodies = [response.json() for response in responses]
                repeated_match = all(
                    canonical_json(body) == canonical_json(bodies[0]) for body in bodies[1:]
                )
                body = bodies[0]
                results = body.get("results", [])
                result_count_match = body.get("result_count") == 3 and len(results) == 3
                retrieval_only = set(body) == {
                    "query",
                    "retrieval_method",
                    "index_run_id",
                    "result_count",
                    "results",
                }

                citation_pass_count = 0
                for result in results:
                    chunk_id = result.get("chunk_id")
                    gold = chunk_by_id.get(chunk_id, {})
                    item = metadata_by_id.get(chunk_id, {})
                    expected_citation_url = (
                        f"{item.get('source_url')}&t={math.floor(float(item.get('start_second', 0)))}s"
                        if item
                        else ""
                    )
                    source_match = result.get("source_url") == item.get("source_url")
                    citation_match = result.get("citation_url") == expected_citation_url
                    timing_match = (
                        result.get("start_second") == item.get("start_second")
                        and result.get("end_second") == item.get("end_second")
                    )
                    text_match = result.get("chunk_text") == gold.get("chunk_text")
                    row_passed = all(
                        (source_match, citation_match, timing_match, text_match)
                    )
                    citation_pass_count += int(row_passed)
                    citation_rows.append(
                        {
                            "question_id": question["question_id"],
                            "answerable": question["answerable"],
                            "rank": result.get("rank"),
                            "chunk_id": chunk_id,
                            "source_url_match": source_match,
                            "citation_url_match": citation_match,
                            "timing_match": timing_match,
                            "chunk_text_match": text_match,
                            "validation_status": "passed" if row_passed else "failed",
                        }
                    )

                if question["answerable"]:
                    expected_ids = json.loads(
                        baseline[question["question_id"]]["top_10_chunk_ids_json"]
                    )[:3]
                    expected_scores = json.loads(
                        baseline[question["question_id"]]["top_10_scores_json"]
                    )[:3]
                    actual_ids = [result.get("chunk_id") for result in results]
                    actual_scores = [float(result.get("score")) for result in results]
                    ids_match = actual_ids == expected_ids
                    max_abs_score_delta = max(
                        abs(actual - expected)
                        for actual, expected in zip(actual_scores, expected_scores, strict=True)
                    )
                    scores_match = len(actual_scores) == 3 and bool(
                        np.allclose(
                            actual_scores,
                            expected_scores,
                            atol=SCORE_TOLERANCE,
                            rtol=0,
                        )
                    )
                    row_passed = all(
                        (
                            status_match,
                            result_count_match,
                            retrieval_only,
                            repeated_match,
                            ids_match,
                            scores_match,
                            citation_pass_count == 3,
                        )
                    )
                    answerable_rows.append(
                        {
                            "question_id": question["question_id"],
                            "http_200_all_runs": status_match,
                            "result_count_is_3": result_count_match,
                            "retrieval_only_contract": retrieval_only,
                            "top_3_ids_match": ids_match,
                            "top_3_scores_match": scores_match,
                            "max_abs_score_delta": f"{max_abs_score_delta:.10f}",
                            "repeated_response_match": repeated_match,
                            "citation_pass_count": citation_pass_count,
                            "expected_top_3_ids_json": canonical_json(expected_ids),
                            "actual_top_3_ids_json": canonical_json(actual_ids),
                            "expected_top_3_scores_json": canonical_json(expected_scores),
                            "actual_top_3_scores_json": canonical_json(
                                [round(score, 8) for score in actual_scores]
                            ),
                            "validation_status": "passed" if row_passed else "failed",
                        }
                    )
                else:
                    forbidden_fields = {
                        "answer",
                        "answerable",
                        "accepted",
                        "rejected",
                        "abstain",
                        "decision",
                    }
                    no_rejection_fields = not (set(body) & forbidden_fields)
                    row_passed = all(
                        (
                            status_match,
                            result_count_match,
                            retrieval_only,
                            no_rejection_fields,
                            repeated_match,
                            citation_pass_count == 3,
                        )
                    )
                    out_of_scope_rows.append(
                        {
                            "question_id": question["question_id"],
                            "http_200_all_runs": status_match,
                            "result_count_is_3": result_count_match,
                            "retrieval_only_contract": retrieval_only,
                            "no_accept_reject_or_answer_fields": no_rejection_fields,
                            "repeated_response_match": repeated_match,
                            "citation_pass_count": citation_pass_count,
                            "actual_top_3_ids_json": canonical_json(
                                [result.get("chunk_id") for result in results]
                            ),
                            "validation_status": "passed" if row_passed else "failed",
                        }
                    )

            for video_id in sorted(video_catalog):
                response = await client.get(f"/videos/{video_id}")
                body = response.json()
                expected = video_catalog[video_id]
                exact_match = body == expected
                video_rows.append(
                    {
                        "video_id": video_id,
                        "http_status": response.status_code,
                        "chunk_count": body.get("chunk_count"),
                        "metadata_exact_match": exact_match,
                        "validation_status": (
                            "passed"
                            if response.status_code == 200 and exact_match
                            else "failed"
                        ),
                    }
                )

            http_cases = [
                ("missing_query", "POST", "/search", {}, None, 422),
                ("empty_query", "POST", "/search", {"query": ""}, None, 422),
                ("whitespace_query", "POST", "/search", {"query": "   "}, None, 422),
                ("null_query", "POST", "/search", {"query": None}, None, 422),
                ("numeric_query", "POST", "/search", {"query": 123}, None, 422),
                (
                    "extra_top_k",
                    "POST",
                    "/search",
                    {"query": "What is computation?", "top_k": 10},
                    None,
                    422,
                ),
                ("malformed_json", "POST", "/search", None, "{", 422),
                ("unknown_video", "GET", "/videos/not-in-corpus", None, None, 404),
                ("missing_video_id", "GET", "/videos/", None, None, 404),
            ]
            for case_id, method, path, json_payload, raw_content, expected_status in http_cases:
                if method == "POST" and raw_content is not None:
                    response = await client.post(
                        path,
                        content=raw_content,
                        headers={"content-type": "application/json"},
                    )
                elif method == "POST":
                    response = await client.post(path, json=json_payload)
                else:
                    response = await client.get(path)
                failure_rows.append(
                    {
                        "layer": "http",
                        "case_id": case_id,
                        "expected_status_or_exception": expected_status,
                        "actual_status_or_exception": response.status_code,
                        "passed": response.status_code == expected_status,
                    }
                )

    failure_rows.extend(startup_failure_rows())
    return {
        ANSWERABLE_FILE: answerable_rows,
        OUT_OF_SCOPE_FILE: out_of_scope_rows,
        VIDEO_FILE: video_rows,
        FAILURE_FILE: failure_rows,
        CITATION_FILE: citation_rows,
    }


def build_manifest(
    serialized_reports: dict[str, bytes],
    report_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    input_files = {
        "evaluation": EVALUATION_FILE,
        "locked_dense_baseline": BASELINE_FILE,
        "index_manifest": PROJECT_ROOT / INDEX_MANIFEST_FILE,
        "retrieval_decision": PROJECT_ROOT / RETRIEVAL_DECISION_FILE,
        "api_contract": PROJECT_ROOT / "docs/design/SEARCH_API_CONTRACT.md",
        "api_schema": PROJECT_ROOT / "schemas/search_api_v1.schema.json",
        "api_service": PROJECT_ROOT / "src/search_api/service.py",
        "api_application": PROJECT_ROOT / "src/search_api/app.py",
    }
    input_hashes = {name: _sha256_file(path) for name, path in input_files.items()}
    run_id = f"mit60001_search_api_{sha256_bytes(canonical_json(input_hashes).encode('utf-8'))[:16]}"
    maximum_score_delta = max(
        float(row["max_abs_score_delta"])
        for row in report_rows[ANSWERABLE_FILE]
    )
    return {
        "$schema": "schemas/search_api_validation_manifest_v2.schema.json",
        "schema_version": "search_api_validation_manifest_v2",
        "validation_run_id": run_id,
        "scope_version": "mit_60001_fall_2016_v1",
        "retrieval_method": "dense_baseline_v1",
        "top_k": 3,
        "score_absolute_tolerance": SCORE_TOLERANCE,
        "maximum_observed_score_delta": maximum_score_delta,
        "repeat_count": REPEAT_COUNT,
        "approved_question_count": 40,
        "answerable_question_count": 35,
        "out_of_scope_question_count": 5,
        "video_count": 38,
        "answerable_top_3_id_match_count": 35,
        "answerable_top_3_score_match_count": 35,
        "repeated_response_match_count": 40,
        "citation_validation_row_count": 120,
        "citation_validation_pass_count": 120,
        "http_failure_case_count": 9,
        "startup_failure_case_count": 7,
        "failure_case_pass_count": 16,
        "input_sha256": input_hashes,
        "report_table_sha256": {
            file_name: sha256_bytes(serialized_reports[file_name])
            for file_name in OUTPUT_FILES
        },
        "validation_status": "passed",
    }


def assert_all_passed(report_rows: dict[str, list[dict[str, Any]]]) -> None:
    expected_counts = {
        ANSWERABLE_FILE: 35,
        OUT_OF_SCOPE_FILE: 5,
        VIDEO_FILE: 38,
        FAILURE_FILE: 16,
        CITATION_FILE: 120,
    }
    for file_name, expected_count in expected_counts.items():
        rows = report_rows[file_name]
        if len(rows) != expected_count:
            raise ValueError(
                f"{file_name} contains {len(rows)} rows; expected {expected_count}"
            )
        status_field = "validation_status" if file_name != FAILURE_FILE else "passed"
        failed_rows = [
            row
            for row in rows
            if (
                row[status_field] != "passed"
                if status_field == "validation_status"
                else not row[status_field]
            )
        ]
        if failed_rows:
            raise ValueError(
                f"{file_name} contains failed validation rows: "
                f"{canonical_json(failed_rows)}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON validation manifest; no files are written by default.",
    )
    outputs.add_argument(
        "--output-dir",
        type=Path,
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    report_rows = asyncio.run(http_validation())
    assert_all_passed(report_rows)
    serialized_reports = {
        file_name: serialize_csv(report_rows[file_name]) for file_name in OUTPUT_FILES
    }
    manifest = build_manifest(serialized_reports, report_rows)
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)

    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )
    if args.output is not None:
        write_atomic(args.output.resolve(), manifest_bytes)
    elif args.output_dir is not None:
        output_dir = args.output_dir.resolve()
        for file_name, content in serialized_reports.items():
            write_atomic(output_dir / file_name, content)
        write_atomic(output_dir / MANIFEST_FILE, manifest_bytes)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
