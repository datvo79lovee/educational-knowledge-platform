"""Validate A1 M2 artifacts without calling Ollama or reading evaluation labels."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.run_evidence_review_a1_experiment import (
    CONTRACT_FILE,
    EXPERIMENT_ROOT,
    FINAL_RESPONSE_SCHEMA_FILE,
    MANIFEST_FILE,
    MANIFEST_SCHEMA_FILE,
    MODEL_DIGEST,
    NUM_CTX,
    PROJECT_ROOT,
    REPORT_ROOT,
    REQUEST_FILE,
    REQUEST_SCHEMA_FILE,
    RUN_LABELS,
    STABILITY_FILE,
    STAGE1_SCHEMA_FILE,
    STAGE2_SCHEMA_FILE,
    THRESHOLDS_FILE,
    artifact_paths,
    compare_runs,
    load_jsonl,
    validate_requests,
)
from src.evidence_review.a1_contracts import (
    A1EntailmentAnalysis,
    A1RequirementAnalysis,
    reduce_a1_decision,
)
from scripts.evaluation.phase8_report_paths import (
    frozen_compatible_sha256,
    legacy_manifest_path,
)


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    requests = load_jsonl(REQUEST_FILE)
    request_by_id = {row["question_id"]: row for row in requests}
    request_schema = json.loads(REQUEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    validate_requests(requests, Draft202012Validator(request_schema))

    manifest_path = PROJECT_ROOT / MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"A1 manifest schema failed: {errors[0].message}")

    input_files = {
        "a1_contracts": PROJECT_ROOT / "src/evidence_review/a1_contracts.py",
        "a1_prompts": PROJECT_ROOT / "src/evidence_review/a1_prompts.py",
        "baseline_manifest": PROJECT_ROOT / "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json",
        "contract": CONTRACT_FILE,
        "final_response_schema": FINAL_RESPONSE_SCHEMA_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "ollama_adapter": PROJECT_ROOT / "src/evidence_review/ollama_provider.py",
        "request_package": REQUEST_FILE,
        "request_schema": REQUEST_SCHEMA_FILE,
        "runtime_script": PROJECT_ROOT / "scripts/evaluation/run_evidence_review_a1_experiment.py",
        "stage1_schema": STAGE1_SCHEMA_FILE,
        "stage2_schema": STAGE2_SCHEMA_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    actual_input_hashes = {
        label: frozen_compatible_sha256(path)
        for label, path in sorted(input_files.items())
    }
    if manifest["input_sha256"] != actual_input_hashes:
        raise ValueError("A1 input hash mismatch")

    final_schema = json.loads(FINAL_RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    stage1_schema = json.loads(STAGE1_SCHEMA_FILE.read_text(encoding="utf-8"))
    stage2_schema = json.loads(STAGE2_SCHEMA_FILE.read_text(encoding="utf-8"))
    final_validator = Draft202012Validator(final_schema)
    stage1_validator = Draft202012Validator(stage1_schema)
    stage2_validator = Draft202012Validator(stage2_schema)
    status_fields = (
        "stage1_json_status",
        "stage1_contract_status",
        "stage1_question_only_status",
        "stage2_json_status",
        "stage2_contract_status",
        "stage2_no_final_decision_status",
        "reducer_status",
        "top3_subset_status",
        "final_response_schema_status",
        "runtime_status",
    )
    results: dict[str, dict[str, list[dict[str, Any]]]] = {}

    run_manifest_by_label = {row["run_label"]: row for row in manifest["runs"]}
    for run_label in RUN_LABELS:
        paths = {key: PROJECT_ROOT / value for key, value in artifact_paths(run_label).items()}
        requirements = load_jsonl(paths["requirements"])
        entailments = load_jsonl(paths["entailment"])
        reviews = load_jsonl(paths["reviews"])
        validations = read_csv(paths["validation"])
        collections = (requirements, entailments, reviews, validations)
        if any(len(rows) != 40 for rows in collections):
            raise ValueError(f"A1 {run_label} must contain 40 rows per artifact")
        if any({row["question_id"] for row in rows} != set(request_by_id) for rows in collections):
            raise ValueError(f"A1 {run_label} question IDs drift")
        if any(
            row["run_label"] != run_label
            or row["error"]
            or any(row[field] != "passed" for field in status_fields)
            for row in validations
        ):
            raise ValueError(f"A1 {run_label} validation contains a failed status")
        if any(int(row["stage1_prompt_eval_count"]) > NUM_CTX for row in validations):
            raise ValueError(f"A1 {run_label} Stage 1 exceeded configured context")
        if any(int(row["stage2_prompt_eval_count"]) > NUM_CTX for row in validations):
            raise ValueError(f"A1 {run_label} Stage 2 exceeded configured context")

        req_by_id = {row["question_id"]: row for row in requirements}
        ent_by_id = {row["question_id"]: row for row in entailments}
        review_by_id = {row["question_id"]: row for row in reviews}
        for question_id, request in request_by_id.items():
            req_record = req_by_id[question_id]
            ent_record = ent_by_id[question_id]
            response = review_by_id[question_id]
            if set(req_record) != {
                "schema_version", "run_label", "question_id", "request_id",
                "prompt_version", "requirements", "prompt_eval_count", "eval_count",
            }:
                raise ValueError(f"Stage 1 artifact contains unexpected fields: {question_id}")
            requirement_payload = {"requirements": req_record["requirements"]}
            if list(stage1_validator.iter_errors(requirement_payload)):
                raise ValueError(f"Stage 1 base schema failed: {run_label}/{question_id}")
            requirement_analysis = A1RequirementAnalysis.model_validate(requirement_payload)
            if set(ent_record) != {
                "schema_version", "run_label", "question_id", "request_id",
                "prompt_version", "top3_chunk_ids", "requirements", "assessments",
                "canonicalization", "prompt_eval_count", "eval_count",
            }:
                raise ValueError(f"Stage 2 artifact contains unexpected fields: {question_id}")
            canonicalization = ent_record["canonicalization"]
            if (
                canonicalization.get("policy")
                != "deduplicate_supporting_chunk_ids_preserve_first_occurrence"
                or not isinstance(canonicalization.get("duplicate_supporting_id_count"), int)
                or canonicalization["duplicate_supporting_id_count"] < 0
                or int(
                    next(
                        row["stage2_duplicate_supporting_id_count"]
                        for row in validations
                        if row["question_id"] == question_id
                    )
                ) != canonicalization["duplicate_supporting_id_count"]
            ):
                raise ValueError(f"Stage 2 canonicalization audit failed: {question_id}")
            entailment_payload = {"assessments": ent_record["assessments"]}
            if list(stage2_validator.iter_errors(entailment_payload)):
                raise ValueError(f"Stage 2 base schema failed: {run_label}/{question_id}")
            if any(key in ent_record for key in ("decision", "accept", "reject")):
                raise ValueError(f"Stage 2 made a final decision: {run_label}/{question_id}")
            entailment_analysis = A1EntailmentAnalysis.model_validate(entailment_payload)
            top3_ids = [row["chunk_id"] for row in request["candidates"]]
            reproduced = reduce_a1_decision(
                requirement_analysis, entailment_analysis, top3_ids
            )
            response_errors = list(final_validator.iter_errors(response))
            if response_errors:
                raise ValueError(f"Final response schema failed: {run_label}/{question_id}")
            if response["top3_chunk_ids"] != top3_ids:
                raise ValueError(f"Top 3 drift: {run_label}/{question_id}")
            if response["retrieval_identity"] != request["retrieval_identity"]:
                raise ValueError(f"Retrieval identity drift: {run_label}/{question_id}")
            if (
                response["decision"] != reproduced.decision
                or response["decision_reason"] != reproduced.decision_reason
                or response["supporting_chunk_ids"] != reproduced.supporting_chunk_ids
            ):
                raise ValueError(f"Reducer reproduction mismatch: {run_label}/{question_id}")
            if response["execution_identity"]["model_identifier"] != (
                f"llama3.2:3b@sha256:{MODEL_DIGEST}"
            ):
                raise ValueError(f"Model identity drift: {run_label}/{question_id}")

        expected_artifacts = {
            legacy_manifest_path(paths[key], PROJECT_ROOT): sha256_file(paths[key])
            for key in ("requirements", "entailment", "reviews", "validation")
        }
        actual_artifacts = {
            row["file"]: row["sha256"]
            for row in run_manifest_by_label[run_label]["output_artifacts"]
        }
        if actual_artifacts != expected_artifacts:
            raise ValueError(f"A1 {run_label} artifact hash mismatch")
        decisions = Counter(row["decision"] for row in reviews)
        if (
            run_manifest_by_label[run_label]["accept_count"] != decisions["accept"]
            or run_manifest_by_label[run_label]["reject_count"] != decisions["reject"]
        ):
            raise ValueError(f"A1 {run_label} decision counts mismatch")
        duplicate_count = sum(
            int(row["stage2_duplicate_supporting_id_count"])
            for row in validations
        )
        if run_manifest_by_label[run_label]["duplicate_supporting_id_count"] != duplicate_count:
            raise ValueError(f"A1 {run_label} canonicalization count mismatch")
        results[run_label] = {
            "requirements": requirements,
            "entailment": entailments,
            "reviews": reviews,
            "validation": validations,
        }

    stability_path = PROJECT_ROOT / STABILITY_FILE
    stability = json.loads(stability_path.read_text(encoding="utf-8"))
    reproduced_stability = compare_runs(results["primary"], results["repeat"])
    if stability != reproduced_stability:
        raise ValueError("A1 stability comparison mismatch")
    manifest_stability = {
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
    }
    if manifest["stability"] != manifest_stability:
        raise ValueError("A1 manifest stability summary mismatch")
    if manifest["output_artifacts"] != [
        {
            "file": legacy_manifest_path(stability_path, PROJECT_ROOT),
            "sha256": sha256_file(stability_path),
        }
    ]:
        raise ValueError("A1 stability artifact hash mismatch")

    api_ps = manifest["operating_condition"]["ollama_api_ps"]
    cli_ps = manifest["operating_condition"]["ollama_cli_ps"]
    if api_ps is not None and api_ps.get("context_length") != NUM_CTX:
        raise ValueError("Ollama API process context does not match configured num_ctx")
    if cli_ps is not None and str(cli_ps.get("context")) != str(NUM_CTX):
        raise ValueError("Ollama CLI process context does not match configured num_ctx")
    if manifest["download_performed"] or manifest["ground_truth_read"]:
        raise ValueError("A1 M2 must not download a model or read Ground Truth")
    if manifest["scope"]["holdout_status"] != "not_created_not_used":
        raise ValueError("A1 M2 must not use a holdout")

    print(json.dumps({
        "experiment_run_id": manifest["experiment_run_id"],
        "primary_decisions": {
            "accept": run_manifest_by_label["primary"]["accept_count"],
            "reject": run_manifest_by_label["primary"]["reject_count"],
        },
        "repeat_decisions": {
            "accept": run_manifest_by_label["repeat"]["accept_count"],
            "reject": run_manifest_by_label["repeat"]["reject_count"],
        },
        "stability": manifest["stability"],
        "configured_num_ctx": manifest["execution_config"]["num_ctx"],
        "ground_truth_read": False,
        "m2_status": manifest["m2_status"],
        "validation_status": "passed",
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
