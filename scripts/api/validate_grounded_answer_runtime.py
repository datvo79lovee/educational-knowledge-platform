"""Validate M2 Grounded Answer runtime bằng hai smoke requests, không đọc benchmark."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.grounded_answer.contracts import (
    GroundedAnswerResponse,
    ModelGroundedDecision,
    validate_supporting_chunk_subset,
)
from src.grounded_answer.prompts import PROMPT_VERSION, SYSTEM_PROMPT
from src.grounded_answer.provider import GenerationProviderResult
from src.grounded_answer.service import (
    API_SCHEMA_VERSION,
    MODEL_OUTPUT_SCHEMA_VERSION,
    NUM_CTX,
    NUM_PREDICT,
    PROVIDER,
    SEED,
    TEMPERATURE,
)
from src.search_api.app import app
from src.search_api.service import RETRIEVAL_METHOD, TOP_K, _sha256_file


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports/20_grounded_answer_runtime"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/grounded_answer_runtime_manifest_v1.schema.json"
MODEL_SCHEMA_FILE = PROJECT_ROOT / "schemas/grounded_answer_model_output_v1.schema.json"
API_SCHEMA_FILE = PROJECT_ROOT / "schemas/grounded_answer_api_v1.schema.json"
VALIDATION_FILE = "grounded_answer_runtime_validation.csv"
SMOKE_OUTPUT_FILE = "grounded_answer_smoke_outputs.jsonl"
MANIFEST_FILE = "grounded_answer_runtime_manifest.json"

SMOKE_CASES = (
    {
        "case_id": "answer_smoke",
        "question": "What is an assertion used for in Python?",
        "expected_decision": "answer",
    },
    {
        "case_id": "abstain_smoke",
        "question": "How do Python type hints work in a FastAPI endpoint?",
        "expected_decision": "abstain",
    },
)


class CountingProvider:
    """Đếm model calls mà không thay đổi payload hoặc retry."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.call_count = 0

    def verify_runtime(self) -> dict[str, Any]:
        return self.delegate.verify_runtime()

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> GenerationProviderResult:
        self.call_count += 1
        return self.delegate.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def serialize_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(row) for row in rows) + "\n").encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def invalid_contract_rows() -> list[dict[str, Any]]:
    top3_ids = ["chunk-1", "chunk-2", "chunk-3"]
    cases = (
        (
            "outside_top3_id",
            {
                "decision": "answer",
                "answer": "answer",
                "supporting_chunk_ids": ["outside"],
                "reason": "reason",
            },
        ),
        (
            "duplicate_ids",
            {
                "decision": "answer",
                "answer": "answer",
                "supporting_chunk_ids": ["chunk-1", "chunk-1"],
                "reason": "reason",
            },
        ),
        (
            "answer_zero_ids",
            {
                "decision": "answer",
                "answer": "answer",
                "supporting_chunk_ids": [],
                "reason": "reason",
            },
        ),
        (
            "abstain_non_empty_answer",
            {
                "decision": "abstain",
                "answer": "answer",
                "supporting_chunk_ids": [],
                "reason": "reason",
            },
        ),
        (
            "abstain_non_empty_ids",
            {
                "decision": "abstain",
                "answer": None,
                "supporting_chunk_ids": ["chunk-1"],
                "reason": "reason",
            },
        ),
    )
    rows: list[dict[str, Any]] = []
    for case_id, payload in cases:
        actual = "accepted_invalid_output"
        try:
            decision = ModelGroundedDecision.model_validate(payload)
            validate_supporting_chunk_subset(decision, top3_ids)
        except (ValidationError, ValueError):
            actual = "contract_failure"
        rows.append(
            {
                "layer": "contract",
                "case_id": case_id,
                "expected": "contract_failure",
                "actual": actual,
                "passed": actual == "contract_failure",
            }
        )
    return rows


def leakage_guard_row() -> dict[str, Any]:
    prohibited = (
        "expected_answer_points",
        "relevant_time_ranges",
        "human_label",
        "evaluation_questions.jsonl",
        "evidence_accept_reject",
    )
    active_files = list((PROJECT_ROOT / "src/grounded_answer").glob("*.py")) + [
        PROJECT_ROOT / "src/search_api/app.py"
    ]
    matches = [
        f"{path.relative_to(PROJECT_ROOT)}:{marker}"
        for path in active_files
        for marker in prohibited
        if marker in path.read_text(encoding="utf-8")
    ]
    return {
        "layer": "leakage",
        "case_id": "active_runtime_source_scan",
        "expected": "no_evaluation_label_access",
        "actual": "none" if not matches else "|".join(matches),
        "passed": not matches,
    }


async def runtime_smoke() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any] | None,
    int,
    str,
]:
    validation_rows: list[dict[str, Any]] = []
    smoke_outputs: list[dict[str, Any]] = []
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with app.router.lifespan_context(app):
        answer_service = app.state.answer_service
        original_provider = answer_service.provider
        runtime = original_provider.verify_runtime()
        counter = CountingProvider(original_provider)
        answer_service.provider = counter
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://grounded-answer.test",
            timeout=240.0,
        ) as client:
            for case in SMOKE_CASES:
                search_response = await client.post(
                    "/search", json={"query": case["question"]}
                )
                answer_response = await client.post(
                    "/answer", json={"question": case["question"]}
                )
                body = answer_response.json()
                if answer_response.status_code == 200:
                    GroundedAnswerResponse.model_validate(body)

                search_body = search_response.json()
                search_by_id = {
                    row["chunk_id"]: row for row in search_body.get("results", [])
                }
                expected_citations = []
                for chunk_id in body.get("supporting_chunk_ids", []):
                    item = search_by_id.get(chunk_id)
                    if item is not None:
                        expected_citations.append(
                            {
                                "chunk_id": item["chunk_id"],
                                "rank": item["rank"],
                                "video_id": item["video_id"],
                                "video_url": item["source_url"],
                                "start": item["start_second"],
                                "end": item["end_second"],
                                "citation_url": item["citation_url"],
                            }
                        )
                expected_citations.sort(key=lambda row: row["rank"])
                public_fields = {
                    "question",
                    "original_query",
                    "retrieval_query",
                    "answer_language",
                    "decision",
                    "answer",
                    "supporting_chunk_ids",
                    "citations",
                    "retrieval",
                }
                checks = {
                    "http_200": answer_response.status_code == 200,
                    "decision": body.get("decision") == case["expected_decision"],
                    "public_contract": set(body) == public_fields,
                    "reason_not_exposed": "reason" not in body,
                    "citation_mapping": body.get("citations") == expected_citations,
                    "search_contract_unchanged": set(search_body)
                    == {"query", "retrieval_method", "index_run_id", "result_count", "results"},
                }
                for check_name, passed in checks.items():
                    validation_rows.append(
                        {
                            "layer": "runtime",
                            "case_id": f"{case['case_id']}:{check_name}",
                            "expected": "passed",
                            "actual": "passed" if passed else "failed",
                            "passed": passed,
                        }
                    )
                smoke_outputs.append(
                    {
                        "schema_version": "grounded_answer_smoke_output_v1",
                        "case_id": case["case_id"],
                        "question": case["question"],
                        "expected_decision": case["expected_decision"],
                        "top3_chunk_ids": [
                            row["chunk_id"] for row in search_body.get("results", [])
                        ],
                        "response": body,
                    }
                )

        process = original_provider.inspect_process()
        index_run_id = answer_service.search_service.index_run_id
        return (
            validation_rows,
            smoke_outputs,
            runtime,
            process,
            counter.call_count,
            index_run_id,
        )


def build_manifest(
    *,
    output_bytes: dict[str, bytes],
    smoke_outputs: list[dict[str, Any]],
    runtime: dict[str, Any],
    process: dict[str, Any] | None,
    model_call_count: int,
    index_run_id: str,
) -> dict[str, Any]:
    input_files = {
        "contracts": PROJECT_ROOT / "src/grounded_answer/contracts.py",
        "prompts": PROJECT_ROOT / "src/grounded_answer/prompts.py",
        "provider": PROJECT_ROOT / "src/grounded_answer/ollama_provider.py",
        "service": PROJECT_ROOT / "src/grounded_answer/service.py",
        "api_application": PROJECT_ROOT / "src/search_api/app.py",
        "model_output_schema": MODEL_SCHEMA_FILE,
        "api_schema": API_SCHEMA_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "runtime_validator": PROJECT_ROOT
        / "scripts/api/validate_grounded_answer_runtime.py",
        "runtime_decision": PROJECT_ROOT
        / "docs/decisions/CANONICAL_RUNTIME_DECISIONS.md",
        "index_manifest": PROJECT_ROOT / "reports/09_embedding/embedding_index_manifest.json",
    }
    input_hashes = {name: _sha256_file(path) for name, path in input_files.items()}
    prompt_hash = sha256_bytes(SYSTEM_PROMPT.encode("utf-8"))
    questions_hash = sha256_bytes(
        canonical_json([row["question"] for row in SMOKE_CASES]).encode("utf-8")
    )
    identity = {
        "input_sha256": input_hashes,
        "model_digest": runtime["digest"],
        "prompt_sha256": prompt_hash,
        "smoke_questions_sha256": questions_hash,
        "inference": [TEMPERATURE, SEED, NUM_CTX, NUM_PREDICT],
    }
    run_id = "mit60001_grounded_answer_runtime_" + sha256_bytes(
        canonical_json(identity).encode("utf-8")
    )[:16]
    decisions = [row["response"]["decision"] for row in smoke_outputs]
    citation_count = sum(len(row["response"]["citations"]) for row in smoke_outputs)
    actual_context = process.get("context_length") if process else None
    return {
        "$schema": "../../schemas/grounded_answer_runtime_manifest_v1.schema.json",
        "schema_version": "grounded_answer_runtime_manifest_v1",
        "runtime_run_id": run_id,
        "scope_version": "mit_60001_fall_2016_v1",
        "implementation_status": "complete_runtime_only_not_quality_evaluated",
        "provider": {
            "name": PROVIDER,
            "api_mode": "ollama_api_chat",
            "ollama_version": runtime["ollama_version"],
            "model": runtime["model"],
            "digest": runtime["digest"],
            "family": runtime["family"],
            "parameter_size": runtime["parameter_size"],
            "quantization_level": runtime["quantization_level"],
        },
        "inference": {
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT,
            "actual_context_length": actual_context,
        },
        "prompt": {"version": PROMPT_VERSION, "sha256": prompt_hash},
        "retrieval": {
            "method": RETRIEVAL_METHOD,
            "top_k": TOP_K,
            "index_run_id": index_run_id,
        },
        "contracts": {
            "model_output_schema_version": MODEL_OUTPUT_SCHEMA_VERSION,
            "api_schema_version": API_SCHEMA_VERSION,
            "invalid_case_count": 5,
            "invalid_case_pass_count": 5,
            "auto_repair_used": False,
        },
        "smoke": {
            "request_count": len(smoke_outputs),
            "model_call_count": model_call_count,
            "answer_count": decisions.count("answer"),
            "abstain_count": decisions.count("abstain"),
            "citation_count": citation_count,
            "smoke_questions_sha256": questions_hash,
        },
        "leakage_guard": {
            "ground_truth_read": False,
            "evaluation_label_read": False,
            "source_scan_status": "passed",
        },
        "input_sha256": input_hashes,
        "output_artifacts": [
            {
                "file": f"reports/20_grounded_answer_runtime/{name}",
                "sha256": sha256_bytes(content),
            }
            for name, content in output_bytes.items()
        ],
        "validation_status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    runtime_rows, smoke_outputs, runtime, process, call_count, index_run_id = asyncio.run(
        runtime_smoke()
    )
    rows = invalid_contract_rows() + [leakage_guard_row()] + runtime_rows
    failed = [row for row in rows if not row["passed"]]
    if call_count != len(SMOKE_CASES):
        failed.append(
            {
                "layer": "runtime",
                "case_id": "one_model_call_per_request",
                "expected": len(SMOKE_CASES),
                "actual": call_count,
                "passed": False,
            }
        )
    if failed:
        raise ValueError("Grounded answer runtime validation failed: " + canonical_json(failed))

    output_bytes = {
        VALIDATION_FILE: serialize_csv(rows),
        SMOKE_OUTPUT_FILE: serialize_jsonl(smoke_outputs),
    }
    manifest = build_manifest(
        output_bytes=output_bytes,
        smoke_outputs=smoke_outputs,
        runtime=runtime,
        process=process,
        model_call_count=call_count,
        index_run_id=index_run_id,
    )
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)

    output_dir = args.output_dir.resolve()
    for name, content in output_bytes.items():
        write_atomic(output_dir / name, content)
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )
    write_atomic(output_dir / MANIFEST_FILE, manifest_bytes)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
