"""Canonicalize reviewed M3 prompt-experiment evidence and freeze final metrics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_V2_ROOT = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2"
REPORT_ROOT = PROJECT_ROOT / "reports/17_evidence_reviewer_prompt_evaluation"

PENDING_FILE = PROMPT_V2_ROOT / "m3_pending_evidence_review.csv"
PRE_AUDIT_FILE = PROMPT_V2_ROOT / "m3_evidence_selection_audit.csv"
THRESHOLDS_FILE = PROMPT_V2_ROOT / "m3_thresholds.json"
REVIEWED_WORKBOOK_FILE = PROMPT_V2_ROOT / (
    "outputs/phase8_m3/phase8_m3_prompt_experiment_evidence_review_reviewed.xlsx"
)
DEFAULT_REVIEW_EXPORT = PROMPT_V2_ROOT / (
    "outputs/phase8_m3/phase8_m3_prompt_experiment_evidence_review_export.json"
)
E0_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
E1_FILE = PROMPT_V2_ROOT / "control_v1_reviews.jsonl"
E2_FILE = PROMPT_V2_ROOT / "candidate_v2_reviews.jsonl"
PRE_METRICS_FILE = REPORT_ROOT / "pre_review_decision_metrics.json"
PRE_MANIFEST_FILE = REPORT_ROOT / "m3_pre_review_manifest.json"
FINAL_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_prompt_m3_final_manifest_v1.schema.json"

CANONICAL_HUMAN_FILE = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/"
    "m3_human_evidence_review_canonical.csv"
)
CANONICAL_EVIDENCE_FILE = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/"
    "m3_evidence_selection_canonical.csv"
)
FINAL_METRICS_FILE = Path("reports/17_evidence_reviewer_prompt_evaluation/final_metrics.json")
FINAL_MANIFEST_FILE = Path("reports/17_evidence_reviewer_prompt_evaluation/m3_final_manifest.json")

EXPECTED_EXCLUSIONS = {
    "mit60001-q-017",
    "mit60001-q-023",
    "mit60001-q-041",
}
VALID_VERDICTS = {"supports", "does_not_support"}
IMMUTABLE_REVIEW_FIELDS = (
    "review_key",
    "question_id",
    "decision_evaluation_scope",
    "question",
    "expected_answer_points",
    "supporting_chunk_id",
    "supporting_rank",
    "supporting_chunk_text",
    "citation_url",
    "e2_reason",
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


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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


def safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def normalized_cell(value: Any) -> str:
    return "" if value is None else str(value)


def summarize_candidate_evidence(
    responses: list[dict[str, Any]], verdicts: dict[tuple[str, str], str]
) -> dict[str, Any]:
    all_pairs = [
        (row["question_id"], chunk_id)
        for row in responses
        for chunk_id in row["supporting_chunk_ids"]
    ]
    gate_pairs = [pair for pair in all_pairs if pair[0] not in EXPECTED_EXCLUSIONS]

    def summarize(pairs: list[tuple[str, str]]) -> dict[str, Any]:
        missing = [pair for pair in pairs if pair not in verdicts]
        if missing:
            raise ValueError(f"Missing final evidence verdicts: {missing[:3]}")
        counts = Counter(verdicts[pair] for pair in pairs)
        return {
            "selected_pair_count": len(pairs),
            "supports_count": counts["supports"],
            "does_not_support_count": counts["does_not_support"],
            "pending_human_review_count": 0,
            "evidence_precision": safe_divide(counts["supports"], len(pairs)),
        }

    return {
        "all_40_questions": summarize(all_pairs),
        "same_37_decision_evaluable_questions": summarize(gate_pairs),
    }


def build(review_export: Path, output_root: Path) -> dict[str, Any]:
    export_bytes = review_export.read_bytes()
    export = json.loads(export_bytes.decode("utf-8"))
    if export.get("schema_version") != "evidence_review_prompt_m3_human_export_v1":
        raise ValueError("Unexpected human-review export schema")
    if export.get("workbook_file") != REVIEWED_WORKBOOK_FILE.relative_to(PROJECT_ROOT).as_posix():
        raise ValueError("Reviewed workbook path drift")
    workbook_sha256 = sha256_file(REVIEWED_WORKBOOK_FILE)
    if export.get("workbook_sha256") != workbook_sha256:
        raise ValueError("Reviewed workbook SHA-256 mismatch")

    pending_rows = load_csv(PENDING_FILE)
    audit_rows = load_csv(PRE_AUDIT_FILE)
    reviewed_rows = export.get("review_rows")
    if not isinstance(reviewed_rows, list) or len(reviewed_rows) != 38:
        raise ValueError("Human review must contain exactly 38 rows")
    pending_by_key = {row["review_key"]: row for row in pending_rows}
    reviewed_by_key = {str(row.get("review_key", "")): row for row in reviewed_rows}
    if len(pending_by_key) != 38 or len(reviewed_by_key) != 38:
        raise ValueError("Duplicate or missing human-review keys")
    if set(reviewed_by_key) != set(pending_by_key):
        raise ValueError("Human-review keys do not match the frozen pending package")

    export_sha256 = sha256_bytes(export_bytes)
    canonical_human: list[dict[str, Any]] = []
    verdict_by_pair: dict[tuple[str, str], str] = {}
    for review_key in sorted(pending_by_key):
        source = pending_by_key[review_key]
        reviewed = reviewed_by_key[review_key]
        for field in IMMUTABLE_REVIEW_FIELDS:
            if normalized_cell(reviewed.get(field)) != normalized_cell(source.get(field)):
                raise ValueError(f"Immutable review field changed: {review_key}.{field}")
        verdict = normalized_cell(reviewed.get("human_entailment_verdict")).strip()
        if verdict == "needs_discussion":
            raise ValueError(f"needs_discussion blocks final gate: {review_key}")
        if verdict not in VALID_VERDICTS:
            raise ValueError(f"Invalid or blank evidence verdict: {review_key}")
        if normalized_cell(reviewed.get("human_review_status")).strip() != "reviewed":
            raise ValueError(f"Human review is incomplete: {review_key}")
        canonical = {
            **source,
            "human_entailment_verdict": verdict,
            "human_notes": normalized_cell(reviewed.get("human_notes")),
            "human_review_status": "reviewed",
            "source_workbook_sha256": workbook_sha256,
            "source_review_export_sha256": export_sha256,
        }
        canonical_human.append(canonical)
        pair = (source["question_id"], source["supporting_chunk_id"])
        if pair in verdict_by_pair:
            raise ValueError(f"Duplicate reviewed question/chunk pair: {pair}")
        verdict_by_pair[pair] = verdict

    canonical_evidence: list[dict[str, Any]] = []
    for row in audit_rows:
        pair = (row["question_id"], row["supporting_chunk_id"])
        if row["human_review_status"] == "canonical_reuse":
            if row["human_entailment_verdict"] not in VALID_VERDICTS:
                raise ValueError(f"Invalid reused canonical verdict: {pair}")
            canonical = {
                **row,
                "source_workbook_sha256": "",
                "source_review_export_sha256": "",
            }
        elif row["human_review_status"] == "pending":
            if pair not in verdict_by_pair:
                raise ValueError(f"Reviewed verdict missing for pending pair: {pair}")
            human = next(
                item
                for item in canonical_human
                if item["question_id"] == pair[0] and item["supporting_chunk_id"] == pair[1]
            )
            canonical = {
                **row,
                "verdict_source": "prompt_v2_m3_human_review",
                "human_entailment_verdict": human["human_entailment_verdict"],
                "human_notes": human["human_notes"],
                "human_review_status": "reviewed",
                "source_workbook_sha256": workbook_sha256,
                "source_review_export_sha256": export_sha256,
            }
        else:
            raise ValueError(f"Unexpected pre-review evidence status: {pair}")
        canonical_evidence.append(canonical)

    if len(canonical_evidence) != 73:
        raise ValueError("Final evidence audit must contain 73 unique E1/E2 pairs")
    complete_verdicts = {
        (row["question_id"], row["supporting_chunk_id"]): row["human_entailment_verdict"]
        for row in canonical_evidence
    }
    if len(complete_verdicts) != 73:
        raise ValueError("Final evidence audit contains duplicate question/chunk pairs")

    pre_metrics = json.loads(PRE_METRICS_FILE.read_text(encoding="utf-8"))
    thresholds = json.loads(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    e2_evidence = summarize_candidate_evidence(load_jsonl(E2_FILE), complete_verdicts)
    limits = thresholds["thresholds"]
    evidence_value = e2_evidence["same_37_decision_evaluable_questions"]["evidence_precision"]
    evidence_passed = evidence_value >= limits["evidence_selection_precision_min"]
    decision_thresholds = pre_metrics["threshold_status"]["decision_thresholds"]
    failed_thresholds = [
        name for name, result in decision_thresholds.items() if not result["passed"]
    ]
    if not evidence_passed:
        failed_thresholds.append("evidence_selection_precision")
    all_passed = not failed_thresholds
    overall = "passes_in_sample_experiment_gate" if all_passed else "failed_candidate"

    human_counts = Counter(row["human_entailment_verdict"] for row in canonical_human)
    final_metrics = {
        "schema_version": "evidence_review_prompt_m3_final_metrics_v1",
        "evaluation_scope": pre_metrics["evaluation_scope"],
        "decision_metrics": pre_metrics["decision_metrics"],
        "evidence_metrics": {
            "locked_baseline_e0": pre_metrics["evidence_metrics_before_new_human_review"]["locked_baseline_e0"],
            "current_control_e1": pre_metrics["evidence_metrics_before_new_human_review"]["current_control_e1"],
            "candidate_v2_e2": e2_evidence,
        },
        "human_review": {
            "reviewed_pair_count": len(canonical_human),
            "supports_count": human_counts["supports"],
            "does_not_support_count": human_counts["does_not_support"],
            "needs_discussion_count": 0,
            "status": "complete",
        },
        "threshold_status": {
            "decision_thresholds": decision_thresholds,
            "evidence_threshold": {
                "value": evidence_value,
                "threshold_min": limits["evidence_selection_precision_min"],
                "passed": evidence_passed,
            },
            "failed_thresholds": failed_thresholds,
            "overall": overall,
        },
        "candidate_result": {
            "status": overall,
            "passes_in_sample_experiment_gate": all_passed,
            "production_ready_claim_allowed": False,
            "generalization_claim_allowed": False,
            "interpretation": (
                thresholds["interpretation_if_passed"]
                if all_passed
                else thresholds["interpretation_if_failed"]
            ),
        },
        "metric_scope_note": (
            "Decision metrics use the same frozen 37 labels. Evidence precision uses "
            "all E2-selected question/chunk pairs from those same 37 questions. "
            "Selections for q-017, q-023 and q-041 remain in the all-40 audit only."
        ),
    }

    output_payloads = {
        CANONICAL_HUMAN_FILE: serialize_csv(canonical_human),
        CANONICAL_EVIDENCE_FILE: serialize_csv(canonical_evidence),
        FINAL_METRICS_FILE: serialize_json(final_metrics),
    }
    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)

    pre_manifest = json.loads(PRE_MANIFEST_FILE.read_text(encoding="utf-8"))
    input_files = {
        "canonicalizer": Path(__file__).resolve(),
        "candidate_v2_e2": E2_FILE,
        "final_manifest_schema": FINAL_SCHEMA_FILE,
        "m3_pre_review_manifest": PRE_MANIFEST_FILE,
        "pending_human_review_package": PENDING_FILE,
        "pre_review_evidence_audit": PRE_AUDIT_FILE,
        "pre_review_metrics": PRE_METRICS_FILE,
        "review_export": review_export,
        "reviewed_workbook": REVIEWED_WORKBOOK_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    input_sha256 = {label: sha256_file(path) for label, path in sorted(input_files.items())}
    final_run_id = "mit60001_evidence_prompt_m3_final_" + sha256_bytes(
        canonical_json(input_sha256).encode("utf-8")
    )[:16]
    manifest = {
        "$schema": "../../schemas/evidence_review_prompt_m3_final_manifest_v1.schema.json",
        "schema_version": "evidence_review_prompt_m3_final_manifest_v1",
        "final_run_id": final_run_id,
        "frozen_pre_review_m3_run_id": pre_manifest["m3_run_id"],
        "frozen_experiment_run_id": pre_manifest["frozen_experiment_run_id"],
        "reviewed_workbook": {
            "file": REVIEWED_WORKBOOK_FILE.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": workbook_sha256,
        },
        "review_export": {
            "file": review_export.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": export_sha256,
        },
        "final_metrics": final_metrics,
        "input_sha256": input_sha256,
        "output_artifacts": [
            {"file": path.as_posix(), "sha256": sha256_bytes(content)}
            for path, content in output_payloads.items()
        ],
        "ground_truth_modified": False,
        "prompt_or_model_modified": False,
        "additional_exclusions_created": False,
        "validation_status": "passed",
        "m3_status": overall,
    }
    schema = json.loads(FINAL_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"Final M3 manifest schema failed: {errors[0].message}")
    write_atomic(output_root / FINAL_MANIFEST_FILE, serialize_json(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-export", type=Path, default=DEFAULT_REVIEW_EXPORT)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build(args.review_export.resolve(), args.output_root.resolve())
    print(canonical_json({
        "final_run_id": manifest["final_run_id"],
        "m3_status": manifest["m3_status"],
        "threshold_status": manifest["final_metrics"]["threshold_status"],
    }))


if __name__ == "__main__":
    main()
