"""Run control V1 và candidate V2 trên cùng Dense Top 3 request package.

Script không đọc calibration, Ground Truth hoặc expected answer points. Control
và candidate dùng cùng model, digest, runtime config và Ollama process để cô lập
tác động của prompt trong môi trường hiện tại.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from dataclasses import dataclass
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
    PROMPT_VERSION as CONTROL_PROMPT_VERSION,
    SYSTEM_PROMPT as CONTROL_SYSTEM_PROMPT,
    build_output_schema,
    build_user_prompt,
)
from src.evidence_review.prompts_v2 import (
    PROMPT_VERSION as CANDIDATE_PROMPT_VERSION,
    SYSTEM_PROMPT as CANDIDATE_SYSTEM_PROMPT,
)


REQUEST_PACKAGE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
REQUEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json"
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / (
    "schemas/evidence_review_prompt_experiment_manifest_v1.schema.json"
)
CONTRACT_FILE = PROJECT_ROOT / "docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md"
BASELINE_MANIFEST_FILE = PROJECT_ROOT / (
    "reports/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
)
EXPERIMENT_ROOT = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2"
)
REPORT_ROOT = Path("reports/16_evidence_reviewer_prompt_experiment")
MANIFEST_FILE = REPORT_ROOT / "prompt_experiment_manifest.json"

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
LOCKED_BASELINE_RUN_ID = "mit60001_evidence_reviewer_0ee5e6a1362fc5c4"
SMOKE_QUESTION_IDS = {
    "mit60001-q-003",
    "mit60001-q-012",
    "mit60001-q-014",
}


@dataclass(frozen=True)
class Variant:
    variant_id: str
    prompt_version: str
    system_prompt: str

    @property
    def output_file(self) -> Path:
        return EXPERIMENT_ROOT / f"{self.variant_id}_reviews.jsonl"

    @property
    def validation_file(self) -> Path:
        return REPORT_ROOT / f"{self.variant_id}_validation.csv"

    @property
    def smoke_output_file(self) -> Path:
        return REPORT_ROOT / f"{self.variant_id}_smoke_outputs.jsonl"

    @property
    def smoke_validation_file(self) -> Path:
        return REPORT_ROOT / f"{self.variant_id}_smoke_validation.csv"


VARIANTS = (
    Variant("control_v1", CONTROL_PROMPT_VERSION, CONTROL_SYSTEM_PROMPT),
    Variant("candidate_v2", CANDIDATE_PROMPT_VERSION, CANDIDATE_SYSTEM_PROMPT),
)


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
    return ("\n".join(canonical_json(record) for record in records) + "\n").encode(
        "utf-8"
    )


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


def validate_requests(
    requests: list[dict[str, Any]], request_validator: Draft202012Validator
) -> None:
    if len(requests) != 40 or len({row["question_id"] for row in requests}) != 40:
        raise ValueError("Request package must contain exactly 40 unique questions")
    prohibited = {
        "expected_answer_points",
        "relevant_time_ranges",
        "answerable",
        "reference_decision",
        "calibration_class",
    }
    for request in requests:
        errors = sorted(
            request_validator.iter_errors(request), key=lambda item: list(item.path)
        )
        if errors:
            raise ValueError(
                f"Request schema failed for {request.get('question_id')}: "
                f"{errors[0].message}"
            )
        leaked = prohibited & set(request)
        if leaked:
            raise ValueError(f"Ground Truth leakage in request: {sorted(leaked)}")


def execution_identity(variant: Variant) -> dict[str, Any]:
    return {
        "provider": PROVIDER,
        "model_identifier": f"{MODEL}@sha256:{MODEL_DIGEST}",
        "api_mode": API_MODE,
        "temperature": TEMPERATURE,
        "reasoning_setting": None,
        "structured_output_schema_version": RESPONSE_SCHEMA_VERSION,
        "prompt_version": variant.prompt_version,
        "contract_version": CONTRACT_VERSION,
    }


def build_response(
    request: dict[str, Any], decision: ReviewerDecision, variant: Variant
) -> dict[str, Any]:
    chunk_ids = [candidate["chunk_id"] for candidate in request["candidates"]]
    validate_candidate_subset(decision, chunk_ids)
    return {
        "schema_version": RESPONSE_SCHEMA_VERSION,
        "review_id": f"review-ollama-{variant.variant_id}-{request['question_id']}",
        "request_id": request["request_id"],
        "question_id": request["question_id"],
        "retrieval_identity": request["retrieval_identity"],
        "top3_chunk_ids": chunk_ids,
        "decision": decision.decision,
        "decision_reason": decision.decision_reason.strip(),
        "supporting_chunk_ids": decision.supporting_chunk_ids,
        "execution_identity": execution_identity(variant),
    }


def run_variant(
    *,
    variant: Variant,
    requests: list[dict[str, Any]],
    provider: OllamaProvider,
    response_validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    responses: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    for request in requests:
        candidate_ids = [row["chunk_id"] for row in request["candidates"]]
        try:
            result = provider.review(
                system_prompt=variant.system_prompt,
                user_prompt=build_user_prompt(request),
                output_schema=build_output_schema(candidate_ids),
            )
            decision = ReviewerDecision.model_validate(json.loads(result.content))
            response = build_response(request, decision, variant)
            errors = sorted(
                response_validator.iter_errors(response), key=lambda item: list(item.path)
            )
            if errors:
                raise ValueError(f"Response schema failed: {errors[0].message}")
            responses.append(response)
            validation_rows.append(
                {
                    "variant_id": variant.variant_id,
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
                    "variant_id": variant.variant_id,
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


def _variant_manifest(
    *,
    variant: Variant,
    runtime: dict[str, Any],
    responses: list[dict[str, Any]],
    output_bytes: bytes,
    validation_bytes: bytes,
) -> dict[str, Any]:
    identity_payload = {
        "request_package_sha256": sha256_file(REQUEST_PACKAGE),
        "runtime": runtime,
        "execution_identity": execution_identity(variant),
        "system_prompt_sha256": sha256_bytes(variant.system_prompt.encode("utf-8")),
        "seed": SEED,
        "num_predict": NUM_PREDICT,
    }
    decisions = Counter(row["decision"] for row in responses)
    return {
        "variant_id": variant.variant_id,
        "prompt_version": variant.prompt_version,
        "system_prompt_sha256": sha256_bytes(variant.system_prompt.encode("utf-8")),
        "runtime_run_id": "mit60001_evidence_reviewer_experiment_"
        + sha256_bytes(canonical_json(identity_payload).encode("utf-8"))[:16],
        "question_count": len(responses),
        "accept_count": decisions["accept"],
        "reject_count": decisions["reject"],
        "failure_count": 0,
        "output_artifacts": [
            {"file": variant.output_file.as_posix(), "sha256": sha256_bytes(output_bytes)},
            {
                "file": variant.validation_file.as_posix(),
                "sha256": sha256_bytes(validation_bytes),
            },
        ],
    }


def _comparison(
    control: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, int]:
    control_by_id = {row["question_id"]: row for row in control}
    candidate_by_id = {row["question_id"]: row for row in candidate}
    if set(control_by_id) != set(candidate_by_id):
        raise ValueError("Variant question IDs differ")
    return {
        "question_count": len(control_by_id),
        "same_top3_count": sum(
            control_by_id[qid]["top3_chunk_ids"]
            == candidate_by_id[qid]["top3_chunk_ids"]
            for qid in control_by_id
        ),
        "decision_change_count": sum(
            control_by_id[qid]["decision"] != candidate_by_id[qid]["decision"]
            for qid in control_by_id
        ),
        "supporting_id_change_count": sum(
            control_by_id[qid]["supporting_chunk_ids"]
            != candidate_by_id[qid]["supporting_chunk_ids"]
            for qid in control_by_id
        ),
    }


def run(mode: str, output_root: Path, timeout_seconds: float) -> dict[str, Any]:
    request_schema = json.loads(REQUEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    for schema in (request_schema, response_schema, manifest_schema):
        Draft202012Validator.check_schema(schema)

    requests = sorted(load_jsonl(REQUEST_PACKAGE), key=lambda row: row["question_id"])
    validate_requests(requests, Draft202012Validator(request_schema))
    selected = (
        [row for row in requests if row["question_id"] in SMOKE_QUESTION_IDS]
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
    response_validator = Draft202012Validator(response_schema)
    results: dict[str, list[dict[str, Any]]] = {}
    validations: dict[str, list[dict[str, Any]]] = {}

    for variant in VARIANTS:
        responses, validation_rows = run_variant(
            variant=variant,
            requests=selected,
            provider=provider,
            response_validator=response_validator,
        )
        failures = sum(row["runtime_status"] == "failed" for row in validation_rows)
        results[variant.variant_id] = responses
        validations[variant.variant_id] = validation_rows
        if mode == "smoke":
            write_atomic(
                output_root / variant.smoke_output_file, serialize_jsonl(responses)
            )
            write_atomic(
                output_root / variant.smoke_validation_file,
                serialize_csv(validation_rows),
            )
        if failures or len(responses) != len(selected):
            if mode == "all":
                write_atomic(
                    output_root / variant.validation_file,
                    serialize_csv(validation_rows),
                )
            raise RuntimeError(
                f"{variant.variant_id} failed for {failures}/{len(selected)} questions"
            )

    if mode == "smoke":
        return {
            "mode": "smoke",
            "question_count_per_variant": len(selected),
            "runtime": runtime,
            "variants": {
                variant.variant_id: dict(
                    Counter(row["decision"] for row in results[variant.variant_id])
                )
                for variant in VARIANTS
            },
            "validation_status": "passed",
        }

    output_payloads: dict[str, tuple[bytes, bytes]] = {}
    variant_manifests: list[dict[str, Any]] = []
    for variant in VARIANTS:
        output_bytes = serialize_jsonl(results[variant.variant_id])
        validation_bytes = serialize_csv(validations[variant.variant_id])
        output_payloads[variant.variant_id] = (output_bytes, validation_bytes)
        variant_manifests.append(
            _variant_manifest(
                variant=variant,
                runtime=runtime,
                responses=results[variant.variant_id],
                output_bytes=output_bytes,
                validation_bytes=validation_bytes,
            )
        )

    input_files = {
        "baseline_manifest": BASELINE_MANIFEST_FILE,
        "contract": CONTRACT_FILE,
        "contracts_module": PROJECT_ROOT / "src/evidence_review/contracts.py",
        "experiment_manifest_schema": MANIFEST_SCHEMA_FILE,
        "ollama_adapter": PROJECT_ROOT / "src/evidence_review/ollama_provider.py",
        "prompt_v1_module": PROJECT_ROOT / "src/evidence_review/prompts.py",
        "prompt_v2_module": PROJECT_ROOT / "src/evidence_review/prompts_v2.py",
        "request_package": REQUEST_PACKAGE,
        "request_schema": REQUEST_SCHEMA_FILE,
        "response_schema": RESPONSE_SCHEMA_FILE,
        "runtime_script": Path(__file__).resolve(),
    }
    input_sha256 = {
        label: sha256_file(path) for label, path in sorted(input_files.items())
    }
    comparison = _comparison(results["control_v1"], results["candidate_v2"])
    experiment_identity = {
        "input_sha256": input_sha256,
        "runtime": runtime,
        "variant_runtime_ids": [row["runtime_run_id"] for row in variant_manifests],
        "output_sha256": {
            variant_id: [sha256_bytes(content) for content in payloads]
            for variant_id, payloads in output_payloads.items()
        },
    }
    baseline_manifest = json.loads(BASELINE_MANIFEST_FILE.read_text(encoding="utf-8"))
    if baseline_manifest.get("runtime_run_id") != LOCKED_BASELINE_RUN_ID:
        raise ValueError("Locked baseline runtime identity drift")
    manifest = {
        "$schema": "../../schemas/evidence_review_prompt_experiment_manifest_v1.schema.json",
        "schema_version": "evidence_review_prompt_experiment_manifest_v1",
        "experiment_run_id": "mit60001_evidence_prompt_experiment_"
        + sha256_bytes(canonical_json(experiment_identity).encode("utf-8"))[:16],
        "experiment_scope": "provider_independent_prompt_comparison_without_ground_truth",
        "baseline_reference": {
            "runtime_run_id": LOCKED_BASELINE_RUN_ID,
            "manifest_sha256": sha256_file(BASELINE_MANIFEST_FILE),
        },
        "runtime": runtime,
        "execution_config": {
            "api_mode": API_MODE,
            "endpoint": ENDPOINT,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_predict": NUM_PREDICT,
            "structured_output_schema_version": RESPONSE_SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
        },
        "input_sha256": input_sha256,
        "variants": variant_manifests,
        "comparison": comparison,
        "validation_status": "passed",
    }
    errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"Experiment manifest schema failed: {errors[0].message}")

    for variant in VARIANTS:
        output_bytes, validation_bytes = output_payloads[variant.variant_id]
        write_atomic(output_root / variant.output_file, output_bytes)
        write_atomic(output_root / variant.validation_file, validation_bytes)
    write_atomic(
        output_root / MANIFEST_FILE,
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
