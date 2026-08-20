"""Validate prompt experiment artifacts without calling Ollama or reading GT."""

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

from scripts.evaluation.phase8_report_paths import (
    frozen_compatible_sha256,
    legacy_manifest_path,
)
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / (
    "schemas/evidence_review_prompt_experiment_manifest_v1.schema.json"
)
MANIFEST_FILE = PROJECT_ROOT / (
    "reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/prompt_experiment_manifest.json"
)
COMPARISON_FILE = PROJECT_ROOT / (
    "reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/mechanical_comparison.json"
)
DELTA_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/decision_deltas.csv"
)
LOCKED_BASELINE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)

VARIANT_FILES = {
    "control_v1": {
        "prompt_version": "evidence_review_prompt_v1",
        "response": PROJECT_ROOT
        / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/control_v1_reviews.jsonl",
        "validation": PROJECT_ROOT
        / "reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/control_v1_validation.csv",
    },
    "candidate_v2": {
        "prompt_version": "evidence_review_prompt_v2_complete_coverage",
        "response": PROJECT_ROOT
        / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl",
        "validation": PROJECT_ROOT
        / "reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/candidate_v2_validation.csv",
    },
}

INPUT_FILES = {
    "baseline_manifest": PROJECT_ROOT
    / "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json",
    "contract": PROJECT_ROOT / "docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md",
    "contracts_module": PROJECT_ROOT / "src/evidence_review/contracts.py",
    "experiment_manifest_schema": MANIFEST_SCHEMA_FILE,
    "ollama_adapter": PROJECT_ROOT / "src/evidence_review/ollama_provider.py",
    "prompt_v1_module": PROJECT_ROOT / "src/evidence_review/prompts.py",
    "prompt_v2_module": PROJECT_ROOT / "src/evidence_review/prompts_v2.py",
    "request_package": REQUEST_FILE,
    "request_schema": PROJECT_ROOT / "schemas/evidence_review_request_v1.schema.json",
    "response_schema": RESPONSE_SCHEMA_FILE,
    "runtime_script": PROJECT_ROOT
    / "scripts/evaluation/run_evidence_review_prompt_experiment.py",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def compare_variants(
    control: dict[str, dict[str, Any]], candidate: dict[str, dict[str, Any]]
) -> dict[str, int]:
    if set(control) != set(candidate):
        raise ValueError("Variant question IDs differ")
    return {
        "question_count": len(control),
        "same_top3_count": sum(
            control[qid]["top3_chunk_ids"] == candidate[qid]["top3_chunk_ids"]
            for qid in control
        ),
        "decision_change_count": sum(
            control[qid]["decision"] != candidate[qid]["decision"] for qid in control
        ),
        "supporting_id_change_count": sum(
            control[qid]["supporting_chunk_ids"]
            != candidate[qid]["supporting_chunk_ids"]
            for qid in control
        ),
    }


def detailed_comparison(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    question_ids = sorted(left)
    if set(question_ids) != set(right):
        raise ValueError("Detailed comparison question IDs differ")
    decision_changes = [
        qid for qid in question_ids if left[qid]["decision"] != right[qid]["decision"]
    ]
    supporting_changes = [
        qid
        for qid in question_ids
        if left[qid]["supporting_chunk_ids"] != right[qid]["supporting_chunk_ids"]
    ]
    return {
        "question_count": len(question_ids),
        "same_top3_count": sum(
            left[qid]["top3_chunk_ids"] == right[qid]["top3_chunk_ids"]
            for qid in question_ids
        ),
        "decision_change_count": len(decision_changes),
        "decision_change_question_ids": decision_changes,
        "supporting_id_change_count": len(supporting_changes),
        "supporting_id_change_question_ids": supporting_changes,
    }


def main() -> None:
    requests = load_jsonl(REQUEST_FILE)
    request_by_id = {row["question_id"]: row for row in requests}
    if len(requests) != 40 or len(request_by_id) != 40:
        raise ValueError("Request package must contain 40 unique questions")

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if manifest_errors:
        raise ValueError(f"Manifest schema failed: {manifest_errors[0].message}")

    for label, path in INPUT_FILES.items():
        if manifest["input_sha256"].get(label) != frozen_compatible_sha256(path):
            raise ValueError(f"Input hash mismatch: {label}")

    response_validator = Draft202012Validator(response_schema)
    manifest_variants = {row["variant_id"]: row for row in manifest["variants"]}
    responses_by_variant: dict[str, dict[str, dict[str, Any]]] = {}
    status_fields = (
        "json_parse_status",
        "decision_contract_status",
        "top3_subset_status",
        "response_schema_status",
        "runtime_status",
    )

    for variant_id, paths in VARIANT_FILES.items():
        responses = load_jsonl(paths["response"])
        response_by_id = {row["question_id"]: row for row in responses}
        if len(responses) != 40 or set(response_by_id) != set(request_by_id):
            raise ValueError(f"{variant_id} must contain the same 40 questions")
        for question_id, response in response_by_id.items():
            errors = sorted(
                response_validator.iter_errors(response), key=lambda item: list(item.path)
            )
            if errors:
                raise ValueError(
                    f"Response schema failed for {variant_id}/{question_id}: "
                    f"{errors[0].message}"
                )
            request = request_by_id[question_id]
            top3_ids = [row["chunk_id"] for row in request["candidates"]]
            if response["top3_chunk_ids"] != top3_ids:
                raise ValueError(f"Top 3 drift for {variant_id}/{question_id}")
            if response["retrieval_identity"] != request["retrieval_identity"]:
                raise ValueError(f"Retrieval identity drift for {variant_id}/{question_id}")
            if not set(response["supporting_chunk_ids"]).issubset(top3_ids):
                raise ValueError(f"Outside-Top-3 ID for {variant_id}/{question_id}")
            if response["execution_identity"]["prompt_version"] != paths["prompt_version"]:
                raise ValueError(f"Prompt identity drift for {variant_id}/{question_id}")

        with paths["validation"].open("r", encoding="utf-8-sig", newline="") as handle:
            validation_rows = list(csv.DictReader(handle))
        if len(validation_rows) != 40:
            raise ValueError(f"{variant_id} validation must contain 40 rows")
        if any(
            row["variant_id"] != variant_id
            or any(row[field] != "passed" for field in status_fields)
            for row in validation_rows
        ):
            raise ValueError(f"{variant_id} validation contains a failed status")

        variant_manifest = manifest_variants[variant_id]
        expected_artifacts = {
            legacy_manifest_path(paths["response"], PROJECT_ROOT): sha256_file(paths["response"]),
            legacy_manifest_path(paths["validation"], PROJECT_ROOT): sha256_file(paths["validation"]),
        }
        actual_artifacts = {
            row["file"]: row["sha256"] for row in variant_manifest["output_artifacts"]
        }
        if actual_artifacts != expected_artifacts:
            raise ValueError(f"Artifact hash mismatch for {variant_id}")
        decisions = Counter(row["decision"] for row in responses)
        if variant_manifest["accept_count"] != decisions["accept"]:
            raise ValueError(f"Accept count mismatch for {variant_id}")
        if variant_manifest["reject_count"] != decisions["reject"]:
            raise ValueError(f"Reject count mismatch for {variant_id}")
        responses_by_variant[variant_id] = response_by_id

    comparison = compare_variants(
        responses_by_variant["control_v1"], responses_by_variant["candidate_v2"]
    )
    if comparison != manifest["comparison"]:
        raise ValueError("Mechanical comparison mismatch")

    mechanical = json.loads(COMPARISON_FILE.read_text(encoding="utf-8"))
    locked_baseline = {
        row["question_id"]: row for row in load_jsonl(LOCKED_BASELINE_FILE)
    }
    expected_mechanical = {
        "locked_baseline_to_current_control": detailed_comparison(
            locked_baseline, responses_by_variant["control_v1"]
        ),
        "current_control_to_candidate_v2": detailed_comparison(
            responses_by_variant["control_v1"], responses_by_variant["candidate_v2"]
        ),
    }
    if mechanical.get("comparisons") != expected_mechanical:
        raise ValueError("E0/E1/E2 mechanical comparison mismatch")
    mechanical_inputs = {
        "request_package": REQUEST_FILE,
        "locked_baseline": LOCKED_BASELINE_FILE,
        "current_control": VARIANT_FILES["control_v1"]["response"],
        "candidate_v2": VARIANT_FILES["candidate_v2"]["response"],
        "builder": PROJECT_ROOT
        / "scripts/evaluation/build_evidence_review_prompt_comparison.py",
    }
    if mechanical.get("input_sha256") != {
        label: frozen_compatible_sha256(path)
        for label, path in sorted(mechanical_inputs.items())
    }:
        raise ValueError("Mechanical comparison input hash mismatch")
    with DELTA_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        delta_rows = list(csv.DictReader(handle))
    if len(delta_rows) != 40:
        raise ValueError("Decision delta artifact must contain 40 rows")
    if mechanical.get("output_artifacts") != [
        {
            "file": legacy_manifest_path(DELTA_FILE, PROJECT_ROOT),
            "sha256": sha256_file(DELTA_FILE),
        }
    ]:
        raise ValueError("Decision delta artifact hash mismatch")
    if mechanical.get("ground_truth_read") is not False:
        raise ValueError("Mechanical comparison must not read Ground Truth")

    print(
        json.dumps(
            {
                "experiment_run_id": manifest["experiment_run_id"],
                "runtime": manifest["runtime"],
                "variants": {
                    row["variant_id"]: {
                        "accept_count": row["accept_count"],
                        "reject_count": row["reject_count"],
                    }
                    for row in manifest["variants"]
                },
                "comparison": comparison,
                "baseline_to_control": expected_mechanical[
                    "locked_baseline_to_current_control"
                ],
                "ground_truth_read": False,
                "validation_status": "passed",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
