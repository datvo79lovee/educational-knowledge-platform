"""Run provider-neutral evidence review bằng Ollama local.

Runtime chỉ đọc request package M2A. Calibration và Ground Truth không phải input
của script này; chúng chỉ được dùng ở milestone đánh giá reviewer sau đó.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence_review.contracts import ReviewerDecision, validate_candidate_subset
from src.evidence_review.ollama_provider import OllamaProvider
from src.evidence_review.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_output_schema,
    build_user_prompt,
)
from src.evidence_review.provider import EvidenceReviewProvider


REQUEST_PACKAGE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
REQUEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json"
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = (
    PROJECT_ROOT / "schemas/evidence_review_runtime_manifest_v1.schema.json"
)
CONTRACT_FILE = (
    PROJECT_ROOT / "docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md"
)

FULL_OUTPUT = Path(
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)
FULL_VALIDATION = Path(
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_validation.csv"
)
FULL_MANIFEST = Path(
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
)
SMOKE_OUTPUT = Path(
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_smoke_outputs.jsonl"
)
SMOKE_VALIDATION = Path(
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_smoke_validation.csv"
)

PROVIDER = "ollama"
MODEL = "llama3.2:3b"
MODEL_DIGEST = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
ENDPOINT = "http://127.0.0.1:11434"
TEMPERATURE = 0.0
SEED = 42
NUM_PREDICT = 512
API_MODE = "ollama_api_chat"
CONTRACT_VERSION = "retrieval_evidence_review_contract_v2"
RESPONSE_SCHEMA_VERSION = "evidence_review_response_v1"
SMOKE_QUESTION_IDS = {
    "mit60001-q-001",  # calibration chưa khóa nhãn
    "mit60001-q-003",  # strong accept
    "mit60001-q-012",  # out-of-scope/strong reject
}


def canonical_json(value: Any) -> str:
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


def execution_identity() -> dict[str, Any]:
    return {
        "provider": PROVIDER,
        "model_identifier": f"{MODEL}@sha256:{MODEL_DIGEST}",
        "api_mode": API_MODE,
        "temperature": TEMPERATURE,
        "reasoning_setting": None,
        "structured_output_schema_version": RESPONSE_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "contract_version": CONTRACT_VERSION,
    }


def build_response(
    request: dict[str, Any], decision: ReviewerDecision
) -> dict[str, Any]:
    chunk_ids = [candidate["chunk_id"] for candidate in request["candidates"]]
    validate_candidate_subset(decision, chunk_ids)
    return {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "review_id": f"review-ollama-{request['question_id']}",
        "request_id": request["request_id"],
        "question_id": request["question_id"],
        "retrieval_identity": request["retrieval_identity"],
        "top3_chunk_ids": chunk_ids,
        "decision": decision.decision,
        "decision_reason": decision.decision_reason.strip(),
        "supporting_chunk_ids": decision.supporting_chunk_ids,
        "execution_identity": execution_identity(),
    }


def run_reviews(
    requests: list[dict[str, Any]],
    provider: EvidenceReviewProvider,
    response_validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    responses: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    for request in requests:
        candidate_ids = [item["chunk_id"] for item in request["candidates"]]
        try:
            result = provider.review(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(request),
                output_schema=build_output_schema(candidate_ids),
            )
            parsed = json.loads(result.content)
            decision = ReviewerDecision.model_validate(parsed)
            response = build_response(request, decision)
            schema_errors = sorted(
                response_validator.iter_errors(response), key=lambda item: list(item.path)
            )
            if schema_errors:
                raise ValueError(f"Response schema failed: {schema_errors[0].message}")
            responses.append(response)
            validation_rows.append(
                {
                    "question_id": request["question_id"],
                    "decision": decision.decision,
                    "supporting_chunk_count": len(decision.supporting_chunk_ids),
                    "prompt_eval_count": result.prompt_eval_count,
                    "eval_count": result.eval_count,
                    "json_parse_status": "passed",
                    "decision_contract_status": "passed",
                    "top3_subset_status": "passed",
                    "response_schema_status": "passed",
                    "runtime_status": "passed",
                    "error": "",
                }
            )
        except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError) as error:
            validation_rows.append(
                {
                    "question_id": request["question_id"],
                    "decision": "",
                    "supporting_chunk_count": "",
                    "prompt_eval_count": "",
                    "eval_count": "",
                    "json_parse_status": "failed",
                    "decision_contract_status": "failed",
                    "top3_subset_status": "failed",
                    "response_schema_status": "failed",
                    "runtime_status": "failed",
                    "error": str(error),
                }
            )
    return responses, validation_rows


def validate_requests(
    requests: list[dict[str, Any]], request_validator: Draft202012Validator
) -> None:
    if len(requests) != 40:
        raise ValueError(f"Expected exactly 40 M2A requests, found {len(requests)}")
    if len({request["question_id"] for request in requests}) != 40:
        raise ValueError("M2A request package contains duplicate question IDs")
    for request in requests:
        errors = sorted(
            request_validator.iter_errors(request), key=lambda item: list(item.path)
        )
        if errors:
            raise ValueError(
                f"M2A request schema failed for {request.get('question_id')}: {errors[0].message}"
            )
        prohibited = {
            "expected_answer_points",
            "relevant_time_ranges",
            "answerable",
            "reference_decision",
            "calibration_class",
        }
        leaked = prohibited & set(request)
        if leaked:
            raise ValueError(f"Ground Truth/calibration leakage in request: {sorted(leaked)}")


def run(mode: str, output_root: Path, timeout_seconds: float) -> dict[str, Any]:
    request_schema = json.loads(REQUEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    for schema in (request_schema, response_schema, manifest_schema):
        Draft202012Validator.check_schema(schema)

    requests = sorted(load_jsonl(REQUEST_PACKAGE), key=lambda item: item["question_id"])
    validate_requests(requests, Draft202012Validator(request_schema))
    selected = (
        [item for item in requests if item["question_id"] in SMOKE_QUESTION_IDS]
        if mode == "smoke"
        else requests
    )
    if mode == "smoke" and len(selected) != len(SMOKE_QUESTION_IDS):
        raise ValueError("Smoke question set is incomplete")

    provider = OllamaProvider(
        endpoint=ENDPOINT,
        model=MODEL,
        expected_digest=MODEL_DIGEST,
        temperature=TEMPERATURE,
        seed=SEED,
        num_predict=NUM_PREDICT,
        timeout_seconds=timeout_seconds,
    )
    runtime = provider.verify_runtime()
    responses, validation_rows = run_reviews(
        selected, provider, Draft202012Validator(response_schema)
    )
    failures = sum(row["runtime_status"] == "failed" for row in validation_rows)

    if mode == "smoke":
        write_atomic(output_root / SMOKE_OUTPUT, serialize_jsonl(responses))
        write_atomic(output_root / SMOKE_VALIDATION, serialize_csv(validation_rows))
        if failures:
            raise RuntimeError(f"Smoke failed for {failures}/{len(selected)} questions")
        return {
            "mode": mode,
            "question_count": len(selected),
            "accept_count": sum(item["decision"] == "accept" for item in responses),
            "reject_count": sum(item["decision"] == "reject" for item in responses),
            "failure_count": failures,
            "runtime": runtime,
            "validation_status": "passed",
        }

    if failures or len(responses) != 40:
        failure_path = output_root / FULL_VALIDATION
        write_atomic(failure_path, serialize_csv(validation_rows))
        raise RuntimeError(f"Full runtime failed for {failures}/{len(selected)} questions")

    response_bytes = serialize_jsonl(responses)
    validation_bytes = serialize_csv(validation_rows)
    input_files = {
        "request_package": REQUEST_PACKAGE,
        "request_schema": REQUEST_SCHEMA_FILE,
        "response_schema": RESPONSE_SCHEMA_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "contract": CONTRACT_FILE,
        "runtime_script": Path(__file__).resolve(),
        "contracts_module": PROJECT_ROOT / "src/evidence_review/contracts.py",
        "provider_protocol": PROJECT_ROOT / "src/evidence_review/provider.py",
        "ollama_adapter": PROJECT_ROOT / "src/evidence_review/ollama_provider.py",
        "prompt_module": PROJECT_ROOT / "src/evidence_review/prompts.py",
    }
    input_sha256 = {
        label: sha256_file(path) for label, path in sorted(input_files.items())
    }
    runtime_identity_payload = {
        "input_sha256": input_sha256,
        "runtime": runtime,
        "execution_identity": execution_identity(),
        "seed": SEED,
        "num_predict": NUM_PREDICT,
    }
    runtime_run_id = "mit60001_evidence_reviewer_" + sha256_bytes(
        canonical_json(runtime_identity_payload).encode("utf-8")
    )[:16]
    decisions = Counter(response["decision"] for response in responses)
    output_payloads = {
        FULL_OUTPUT: response_bytes,
        FULL_VALIDATION: validation_bytes,
    }
    manifest = {
        "$schema": "../../schemas/evidence_review_runtime_manifest_v1.schema.json",
        "schema_version": "evidence_review_runtime_manifest_v1",
        "runtime_run_id": runtime_run_id,
        "provider": PROVIDER,
        "runtime": runtime,
        "execution_config": {
            "api_mode": API_MODE,
            "endpoint": ENDPOINT,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_predict": NUM_PREDICT,
            "structured_output_schema_version": RESPONSE_SCHEMA_VERSION,
            "prompt_version": PROMPT_VERSION,
            "contract_version": CONTRACT_VERSION,
        },
        "input_sha256": input_sha256,
        "output_artifacts": [
            {"file": path.as_posix(), "sha256": sha256_bytes(content)}
            for path, content in output_payloads.items()
        ],
        "question_count": len(responses),
        "accept_count": decisions["accept"],
        "reject_count": decisions["reject"],
        "failure_count": failures,
        "validation_status": "passed",
    }
    manifest_errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if manifest_errors:
        raise ValueError(f"Runtime manifest schema failed: {manifest_errors[0].message}")

    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)
    write_atomic(
        output_root / FULL_MANIFEST,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "all"), required=True)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(args.mode, args.output_root.resolve(), args.timeout_seconds)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
