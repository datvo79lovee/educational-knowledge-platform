"""Run the A1 two-stage evidence reviewer without reading evaluation labels or GT."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence_review.a1_contracts import (
    A1EntailmentAnalysis,
    A1RequirementAnalysis,
    canonicalize_entailment_payload,
    reduce_a1_decision,
)
from src.evidence_review.a1_prompts import (
    ARCHITECTURE_VERSION,
    STAGE1_PROMPT_VERSION,
    STAGE1_SYSTEM_PROMPT,
    STAGE2_PROMPT_VERSION,
    STAGE2_SYSTEM_PROMPT,
    build_stage1_output_schema,
    build_stage1_user_prompt,
    build_stage2_output_schema,
    build_stage2_user_prompt,
)
from src.evidence_review.contracts import ReviewerDecision, validate_candidate_subset
from src.evidence_review.ollama_provider import OllamaProvider


REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
REQUEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json"
FINAL_RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
STAGE1_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_a1_requirement_analysis_v1.schema.json"
STAGE2_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_a1_entailment_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_a1_experiment_manifest_v1.schema.json"
THRESHOLDS_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_thresholds.json"
)
BASELINE_MANIFEST_FILE = PROJECT_ROOT / (
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
)
CONTRACT_FILE = PROJECT_ROOT / "docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md"

EXPERIMENT_ROOT = Path("evaluation/review/evidence_accept_reject/experiments/a1_two_stage")
REPORT_ROOT = Path("reports/phase_08_evidence_reviewer/18_evidence_reviewer_a1_experiment")
MANIFEST_FILE = REPORT_ROOT / "a1_experiment_manifest.json"
STABILITY_FILE = REPORT_ROOT / "a1_stability_comparison.json"

PROVIDER = "ollama"
MODEL = "llama3.2:3b"
MODEL_DIGEST = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
ENDPOINT = "http://127.0.0.1:11434"
TEMPERATURE = 0.0
SEED = 42
NUM_PREDICT = 512
NUM_CTX = 4096
API_MODE = "ollama_api_chat"
FINAL_RESPONSE_SCHEMA_VERSION = "evidence_review_response_v1"
CONTRACT_VERSION = "retrieval_evidence_review_contract_v2"
EXPECTED_EXCLUSIONS = ["mit60001-q-017", "mit60001-q-023", "mit60001-q-041"]
SMOKE_IDS = {"mit60001-q-003", "mit60001-q-012", "mit60001-q-014"}
RUN_LABELS = ("primary", "repeat")


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


def serialize_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def artifact_paths(run_label: str) -> dict[str, Path]:
    return {
        "requirements": EXPERIMENT_ROOT / f"{run_label}_requirements.jsonl",
        "entailment": EXPERIMENT_ROOT / f"{run_label}_entailment.jsonl",
        "reviews": EXPERIMENT_ROOT / f"{run_label}_reviews.jsonl",
        "validation": REPORT_ROOT / f"{run_label}_validation.csv",
    }


def validate_requests(
    requests: list[dict[str, Any]], validator: Draft202012Validator
) -> None:
    if len(requests) != 40 or len({row["question_id"] for row in requests}) != 40:
        raise ValueError("A1 requires exactly 40 unique development requests")
    prohibited = {
        "expected_answer_points",
        "relevant_time_ranges",
        "answerable",
        "reference_decision",
        "calibration_class",
        "expected_decision",
        "human_entailment_verdict",
    }
    retrieval_identities = set()
    for request in requests:
        errors = sorted(validator.iter_errors(request), key=lambda item: list(item.path))
        if errors:
            raise ValueError(
                f"Request schema failed for {request.get('question_id')}: {errors[0].message}"
            )
        leaked = prohibited & set(request)
        if leaked:
            raise ValueError(f"Evaluation leakage in request: {sorted(leaked)}")
        if len(request["candidates"]) != 3:
            raise ValueError("A1 requires Dense Top 3 for every request")
        retrieval_identities.add(canonical_json(request["retrieval_identity"]))
    if len(retrieval_identities) != 1:
        raise ValueError("Retrieval identity must be frozen across all requests")


def execution_identity() -> dict[str, Any]:
    return {
        "provider": PROVIDER,
        "model_identifier": f"{MODEL}@sha256:{MODEL_DIGEST}",
        "api_mode": API_MODE,
        "temperature": TEMPERATURE,
        "reasoning_setting": None,
        "structured_output_schema_version": FINAL_RESPONSE_SCHEMA_VERSION,
        "prompt_version": ARCHITECTURE_VERSION,
        "contract_version": CONTRACT_VERSION,
    }


def build_final_response(
    request: dict[str, Any], decision: ReviewerDecision
) -> dict[str, Any]:
    top3_ids = [row["chunk_id"] for row in request["candidates"]]
    validate_candidate_subset(decision, top3_ids)
    return {
        "schema_version": FINAL_RESPONSE_SCHEMA_VERSION,
        "review_id": f"review-ollama-a1-{request['question_id']}",
        "request_id": request["request_id"],
        "question_id": request["question_id"],
        "retrieval_identity": request["retrieval_identity"],
        "top3_chunk_ids": top3_ids,
        "decision": decision.decision,
        "decision_reason": decision.decision_reason,
        "supporting_chunk_ids": decision.supporting_chunk_ids,
        "execution_identity": execution_identity(),
    }


def run_pass(
    *,
    run_label: str,
    requests: list[dict[str, Any]],
    provider: OllamaProvider,
    stage1_base_validator: Draft202012Validator,
    stage2_base_validator: Draft202012Validator,
    final_validator: Draft202012Validator,
) -> dict[str, list[dict[str, Any]]]:
    requirement_records: list[dict[str, Any]] = []
    entailment_records: list[dict[str, Any]] = []
    final_responses: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []

    for request in requests:
        row: dict[str, Any] = {
            "run_label": run_label,
            "question_id": request["question_id"],
            "requirement_count": "",
            "decision": "",
            "supporting_chunk_count": "",
            "stage1_prompt_eval_count": "",
            "stage1_eval_count": "",
            "stage2_prompt_eval_count": "",
            "stage2_eval_count": "",
            "stage2_duplicate_supporting_id_count": "",
            "stage1_json_status": "failed",
            "stage1_contract_status": "failed",
            "stage1_question_only_status": "passed",
            "stage2_json_status": "failed",
            "stage2_contract_status": "failed",
            "stage2_no_final_decision_status": "passed",
            "reducer_status": "failed",
            "top3_subset_status": "failed",
            "final_response_schema_status": "failed",
            "runtime_status": "failed",
            "error": "",
        }
        try:
            stage1_schema = build_stage1_output_schema()
            stage1_result = provider.review(
                system_prompt=STAGE1_SYSTEM_PROMPT,
                user_prompt=build_stage1_user_prompt(request["question"]),
                output_schema=stage1_schema,
            )
            row["stage1_prompt_eval_count"] = stage1_result.prompt_eval_count
            row["stage1_eval_count"] = stage1_result.eval_count
            stage1_raw = json.loads(stage1_result.content)
            row["stage1_json_status"] = "passed"
            dynamic_stage1_errors = sorted(
                Draft202012Validator(stage1_schema).iter_errors(stage1_raw),
                key=lambda item: list(item.path),
            )
            base_stage1_errors = sorted(
                stage1_base_validator.iter_errors(stage1_raw),
                key=lambda item: list(item.path),
            )
            if dynamic_stage1_errors or base_stage1_errors:
                error = (dynamic_stage1_errors or base_stage1_errors)[0]
                raise ValueError(f"Stage 1 schema failed: {error.message}")
            requirement_analysis = A1RequirementAnalysis.model_validate(stage1_raw)
            row["stage1_contract_status"] = "passed"
            row["requirement_count"] = len(requirement_analysis.requirements)

            requirement_ids = [item.requirement_id for item in requirement_analysis.requirements]
            top3_ids = [item["chunk_id"] for item in request["candidates"]]
            stage2_schema = build_stage2_output_schema(requirement_ids, top3_ids)
            stage2_result = provider.review(
                system_prompt=STAGE2_SYSTEM_PROMPT,
                user_prompt=build_stage2_user_prompt(
                    request["question"], requirement_analysis, request["candidates"]
                ),
                output_schema=stage2_schema,
            )
            row["stage2_prompt_eval_count"] = stage2_result.prompt_eval_count
            row["stage2_eval_count"] = stage2_result.eval_count
            stage2_raw = json.loads(stage2_result.content)
            row["stage2_json_status"] = "passed"
            if "decision" in stage2_raw or "accept" in stage2_raw or "reject" in stage2_raw:
                raise ValueError("Stage 2 must not produce a final decision")
            stage2_canonical, duplicate_id_count = canonicalize_entailment_payload(
                stage2_raw
            )
            row["stage2_duplicate_supporting_id_count"] = duplicate_id_count
            dynamic_stage2_errors = sorted(
                Draft202012Validator(stage2_schema).iter_errors(stage2_canonical),
                key=lambda item: list(item.path),
            )
            base_stage2_errors = sorted(
                stage2_base_validator.iter_errors(stage2_canonical),
                key=lambda item: list(item.path),
            )
            if dynamic_stage2_errors or base_stage2_errors:
                error = (dynamic_stage2_errors or base_stage2_errors)[0]
                raise ValueError(f"Stage 2 schema failed: {error.message}")
            entailment_analysis = A1EntailmentAnalysis.model_validate(stage2_canonical)
            decision = reduce_a1_decision(
                requirement_analysis, entailment_analysis, top3_ids
            )
            row["stage2_contract_status"] = "passed"
            row["reducer_status"] = "passed"
            row["top3_subset_status"] = "passed"

            final_response = build_final_response(request, decision)
            final_errors = sorted(
                final_validator.iter_errors(final_response),
                key=lambda item: list(item.path),
            )
            if final_errors:
                raise ValueError(f"Final response schema failed: {final_errors[0].message}")
            row["final_response_schema_status"] = "passed"
            row["runtime_status"] = "passed"
            row["decision"] = decision.decision
            row["supporting_chunk_count"] = len(decision.supporting_chunk_ids)

            requirement_records.append({
                "schema_version": "evidence_review_a1_requirement_analysis_v1",
                "run_label": run_label,
                "question_id": request["question_id"],
                "request_id": request["request_id"],
                "prompt_version": STAGE1_PROMPT_VERSION,
                "requirements": [item.model_dump() for item in requirement_analysis.requirements],
                "prompt_eval_count": stage1_result.prompt_eval_count,
                "eval_count": stage1_result.eval_count,
            })
            entailment_records.append({
                "schema_version": "evidence_review_a1_entailment_v1",
                "run_label": run_label,
                "question_id": request["question_id"],
                "request_id": request["request_id"],
                "prompt_version": STAGE2_PROMPT_VERSION,
                "top3_chunk_ids": top3_ids,
                "requirements": [item.model_dump() for item in requirement_analysis.requirements],
                "assessments": [item.model_dump() for item in entailment_analysis.assessments],
                "canonicalization": {
                    "policy": "deduplicate_supporting_chunk_ids_preserve_first_occurrence",
                    "duplicate_supporting_id_count": duplicate_id_count,
                },
                "prompt_eval_count": stage2_result.prompt_eval_count,
                "eval_count": stage2_result.eval_count,
            })
            final_responses.append(final_response)
        except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError) as error:
            row["error"] = str(error)
        validation_rows.append(row)
        print(
            canonical_json({
                "run_label": run_label,
                "question_id": request["question_id"],
                "runtime_status": row["runtime_status"],
            }),
            flush=True,
        )

    return {
        "requirements": requirement_records,
        "entailment": entailment_records,
        "reviews": final_responses,
        "validation": validation_rows,
    }


def compare_runs(
    primary: dict[str, list[dict[str, Any]]],
    repeat: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    def by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {row["question_id"]: row for row in records}

    p_req, r_req = by_id(primary["requirements"]), by_id(repeat["requirements"])
    p_ent, r_ent = by_id(primary["entailment"]), by_id(repeat["entailment"])
    p_final, r_final = by_id(primary["reviews"]), by_id(repeat["reviews"])
    if not (set(p_req) == set(r_req) == set(p_ent) == set(r_ent) == set(p_final) == set(r_final)):
        raise ValueError("Primary and repeat question IDs differ")
    question_ids = sorted(p_final)
    stage1_changed = [
        qid for qid in question_ids if p_req[qid]["requirements"] != r_req[qid]["requirements"]
    ]
    stage2_changed = [
        qid
        for qid in question_ids
        if (
            p_ent[qid]["assessments"] != r_ent[qid]["assessments"]
            or p_ent[qid]["canonicalization"] != r_ent[qid]["canonicalization"]
        )
    ]
    final_changed = [qid for qid in question_ids if p_final[qid] != r_final[qid]]
    decision_changed = [
        qid for qid in question_ids if p_final[qid]["decision"] != r_final[qid]["decision"]
    ]
    supporting_changed = [
        qid
        for qid in question_ids
        if p_final[qid]["supporting_chunk_ids"] != r_final[qid]["supporting_chunk_ids"]
    ]
    return {
        "schema_version": "evidence_review_a1_stability_v1",
        "question_count": len(question_ids),
        "stage1_exact_match_count": len(question_ids) - len(stage1_changed),
        "stage1_changed_question_ids": stage1_changed,
        "stage2_exact_match_count": len(question_ids) - len(stage2_changed),
        "stage2_changed_question_ids": stage2_changed,
        "final_response_exact_match_count": len(question_ids) - len(final_changed),
        "final_response_changed_question_ids": final_changed,
        "decision_change_count": len(decision_changed),
        "decision_change_question_ids": decision_changed,
        "supporting_id_change_count": len(supporting_changed),
        "supporting_id_change_question_ids": supporting_changed,
        "best_of_or_voting_used": False,
        "primary_run_is_canonical": True,
    }


def inspect_ollama_cli_ps() -> dict[str, Any] | None:
    candidates: list[Path] = []
    resolved = shutil.which("ollama")
    if resolved:
        candidates.append(Path(resolved))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe")
    executable = next((path for path in candidates if path.exists()), None)
    if executable is None:
        return None
    completed = subprocess.run(
        [str(executable), "ps"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return None
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    headers = re.split(r"\s{2,}", lines[0])
    values = re.split(r"\s{2,}", lines[1])
    parsed = dict(zip(headers, values))
    return {
        "name": parsed.get("NAME"),
        "id": parsed.get("ID"),
        "size": parsed.get("SIZE"),
        "processor": parsed.get("PROCESSOR"),
        "context": parsed.get("CONTEXT"),
    }


def run(mode: str, output_root: Path, timeout_seconds: float) -> dict[str, Any]:
    schemas = {
        "request": json.loads(REQUEST_SCHEMA_FILE.read_text(encoding="utf-8")),
        "final": json.loads(FINAL_RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8")),
        "stage1": json.loads(STAGE1_SCHEMA_FILE.read_text(encoding="utf-8")),
        "stage2": json.loads(STAGE2_SCHEMA_FILE.read_text(encoding="utf-8")),
        "manifest": json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8")),
    }
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    requests = sorted(load_jsonl(REQUEST_FILE), key=lambda row: row["question_id"])
    validate_requests(requests, Draft202012Validator(schemas["request"]))
    selected = (
        [row for row in requests if row["question_id"] in SMOKE_IDS]
        if mode == "smoke"
        else requests
    )
    if mode == "smoke" and len(selected) != len(SMOKE_IDS):
        raise ValueError("Smoke set is incomplete")

    provider = OllamaProvider(
        endpoint=ENDPOINT,
        model=MODEL,
        expected_digest=MODEL_DIGEST,
        temperature=TEMPERATURE,
        seed=SEED,
        num_predict=NUM_PREDICT,
        num_ctx=NUM_CTX,
        timeout_seconds=timeout_seconds,
    )
    runtime = provider.verify_runtime()
    runtime["model_context_capability"] = provider.inspect_model_context_capability()
    if runtime["model_context_capability"] != 131072:
        raise ValueError("Unexpected model context capability")

    validators = {
        "stage1": Draft202012Validator(schemas["stage1"]),
        "stage2": Draft202012Validator(schemas["stage2"]),
        "final": Draft202012Validator(schemas["final"]),
    }
    labels = ("smoke",) if mode == "smoke" else RUN_LABELS
    results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for label in labels:
        result = run_pass(
            run_label=label,
            requests=selected,
            provider=provider,
            stage1_base_validator=validators["stage1"],
            stage2_base_validator=validators["stage2"],
            final_validator=validators["final"],
        )
        failures = sum(row["runtime_status"] != "passed" for row in result["validation"])
        if mode == "smoke":
            smoke_paths = {
                "requirements": REPORT_ROOT / "smoke_requirements.jsonl",
                "entailment": REPORT_ROOT / "smoke_entailment.jsonl",
                "reviews": REPORT_ROOT / "smoke_reviews.jsonl",
                "validation": REPORT_ROOT / "smoke_validation.csv",
            }
            for key, path in smoke_paths.items():
                content = (
                    serialize_csv(result[key])
                    if key == "validation"
                    else serialize_jsonl(result[key])
                )
                write_atomic(output_root / path, content)
        elif failures:
            write_atomic(
                output_root / artifact_paths(label)["validation"],
                serialize_csv(result["validation"]),
            )
        if failures or len(result["reviews"]) != len(selected):
            raise RuntimeError(f"A1 {label} failed for {failures}/{len(selected)} questions")
        results[label] = result

    if mode == "smoke":
        decisions = Counter(row["decision"] for row in results["smoke"]["reviews"])
        return {
            "mode": "smoke",
            "question_count": len(selected),
            "model_call_count": len(selected) * 2,
            "accept_count": decisions["accept"],
            "reject_count": decisions["reject"],
            "configured_num_ctx": NUM_CTX,
            "operating_condition": {
                "ollama_api_ps": provider.inspect_process(),
                "ollama_cli_ps": inspect_ollama_cli_ps(),
            },
            "ground_truth_read": False,
            "validation_status": "passed",
        }

    payloads: dict[str, bytes] = {}
    run_manifests: list[dict[str, Any]] = []
    for label in RUN_LABELS:
        paths = artifact_paths(label)
        run_payloads = {
            "requirements": serialize_jsonl(results[label]["requirements"]),
            "entailment": serialize_jsonl(results[label]["entailment"]),
            "reviews": serialize_jsonl(results[label]["reviews"]),
            "validation": serialize_csv(results[label]["validation"]),
        }
        for key, content in run_payloads.items():
            payloads[paths[key].as_posix()] = content
            write_atomic(output_root / paths[key], content)
        decisions = Counter(row["decision"] for row in results[label]["reviews"])
        run_manifests.append({
            "run_label": label,
            "question_count": 40,
            "accept_count": decisions["accept"],
            "reject_count": decisions["reject"],
            "failure_count": 0,
            "model_call_count": 80,
            "duplicate_supporting_id_count": sum(
                int(row["stage2_duplicate_supporting_id_count"])
                for row in results[label]["validation"]
            ),
            "output_artifacts": [
                {"file": paths[key].as_posix(), "sha256": sha256_bytes(run_payloads[key])}
                for key in ("requirements", "entailment", "reviews", "validation")
            ],
        })

    stability = compare_runs(results["primary"], results["repeat"])
    stability_bytes = serialize_json(stability)
    write_atomic(output_root / STABILITY_FILE, stability_bytes)

    thresholds = json.loads(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    if thresholds["decision_evaluation_scope"] != {
        "evaluated_question_count": 37,
        "excluded_question_ids": EXPECTED_EXCLUSIONS,
        "additional_exclusions_allowed": False,
    }:
        raise ValueError("Frozen M3 evaluation scope drift")
    if thresholds["thresholds"] != {
        "response_schema_valid_rate_min": 1.0,
        "outside_top3_supporting_id_count_max": 0,
        "ground_truth_leakage_count_max": 0,
        "false_accept_rate_max": 0.25,
        "accept_recall_min": 0.75,
        "evidence_selection_precision_min": 0.85,
    }:
        raise ValueError("Frozen quality thresholds drift")

    input_files = {
        "a1_contracts": PROJECT_ROOT / "src/evidence_review/a1_contracts.py",
        "a1_prompts": PROJECT_ROOT / "src/evidence_review/a1_prompts.py",
        "baseline_manifest": BASELINE_MANIFEST_FILE,
        "contract": CONTRACT_FILE,
        "final_response_schema": FINAL_RESPONSE_SCHEMA_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "ollama_adapter": PROJECT_ROOT / "src/evidence_review/ollama_provider.py",
        "request_package": REQUEST_FILE,
        "request_schema": REQUEST_SCHEMA_FILE,
        "runtime_script": Path(__file__).resolve(),
        "stage1_schema": STAGE1_SCHEMA_FILE,
        "stage2_schema": STAGE2_SCHEMA_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    input_sha256 = {label: sha256_file(path) for label, path in sorted(input_files.items())}
    operating_condition = {
        "ollama_api_ps": provider.inspect_process(),
        "ollama_cli_ps": inspect_ollama_cli_ps(),
    }
    retrieval_identity = requests[0]["retrieval_identity"]
    experiment_identity = {
        "input_sha256": input_sha256,
        "runtime": runtime,
        "execution_config": {
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_predict": NUM_PREDICT,
            "num_ctx": NUM_CTX,
        },
        "output_sha256": {
            file_name: sha256_bytes(content) for file_name, content in sorted(payloads.items())
        },
        "stability_sha256": sha256_bytes(stability_bytes),
    }
    manifest = {
        "$schema": "../../schemas/evidence_review_a1_experiment_manifest_v1.schema.json",
        "schema_version": "evidence_review_a1_experiment_manifest_v1",
        "experiment_run_id": "mit60001_evidence_a1_experiment_"
        + sha256_bytes(canonical_json(experiment_identity).encode("utf-8"))[:16],
        "candidate_id": "a1_two_stage_coverage_entailment_v1",
        "experiment_type": "architecture_bundle",
        "scope": {
            "development_request_count": 40,
            "decision_evaluable_count": 37,
            "excluded_question_ids": EXPECTED_EXCLUSIONS,
            "holdout_status": "not_created_not_used",
        },
        "architecture": {
            "stage1": "question_only_requirement_analysis",
            "stage2": "requirement_by_evidence_entailment_without_final_decision",
            "stage2_normalization": "deduplicate_supporting_chunk_ids_preserve_first_occurrence",
            "reducer": "accept_iff_all_requirements_supported",
        },
        "variables_frozen": {
            "model": MODEL,
            "model_digest": MODEL_DIGEST,
            "request_package_sha256": sha256_file(REQUEST_FILE),
            "retrieval_identity": retrieval_identity,
            "final_response_schema_version": FINAL_RESPONSE_SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "quality_thresholds_sha256": sha256_file(THRESHOLDS_FILE),
            "ground_truth_modified": False,
            "additional_exclusions_created": False,
        },
        "execution_config": {
            "api_mode": API_MODE,
            "endpoint": ENDPOINT,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "num_predict": NUM_PREDICT,
            "num_ctx": NUM_CTX,
            "repeat_policy": "primary_frozen_repeat_stability_only_no_voting",
            "structured_output": "json_schema",
        },
        "runtime": runtime,
        "operating_condition": operating_condition,
        "runs": run_manifests,
        "stability": {
            key: stability[key]
            for key in (
                "question_count",
                "stage1_exact_match_count",
                "stage2_exact_match_count",
                "final_response_exact_match_count",
                "decision_change_count",
                "supporting_id_change_count",
                "best_of_or_voting_used",
            )
        },
        "input_sha256": input_sha256,
        "output_artifacts": [
            {"file": STABILITY_FILE.as_posix(), "sha256": sha256_bytes(stability_bytes)}
        ],
        "download_performed": False,
        "ground_truth_read": False,
        "validation_status": "passed",
        "m2_status": "complete_runtime_only_not_quality_evaluated",
    }
    errors = sorted(
        Draft202012Validator(schemas["manifest"]).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"A1 manifest schema failed: {errors[0].message}")
    write_atomic(output_root / MANIFEST_FILE, serialize_json(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "all"), required=True)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(args.mode, args.output_root.resolve(), args.timeout_seconds)
    if args.mode == "all":
        result = {
            "experiment_run_id": result["experiment_run_id"],
            "runs": result["runs"],
            "stability": result["stability"],
            "operating_condition": result["operating_condition"],
            "ground_truth_read": result["ground_truth_read"],
            "m2_status": result["m2_status"],
            "validation_status": result["validation_status"],
        }
    print(canonical_json(result))


if __name__ == "__main__":
    main()
