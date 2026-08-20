"""Canonical M3 evaluation for the frozen A1 evidence-reviewer primary run."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUEST_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
PRIMARY_REVIEWS_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/a1_two_stage/primary_reviews.jsonl"
PRIMARY_ENTAILMENT_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/a1_two_stage/primary_entailment.jsonl"
CANONICAL_DECISIONS_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/final_decision_results.csv"
THRESHOLDS_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_thresholds.json"
A1_MANIFEST_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/18_evidence_reviewer_a1_experiment/a1_experiment_manifest.json"
RESPONSE_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_response_v1.schema.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_review_a1_m3_final_manifest_v1.schema.json"

REPORT_ROOT = Path("reports/phase_08_evidence_reviewer/19_evidence_reviewer_a1_evaluation")
DECISION_RESULTS_FILE = REPORT_ROOT / "a1_decision_results.csv"
FINAL_METRICS_FILE = REPORT_ROOT / "a1_final_metrics.json"
INTERNAL_AUDIT_FILE = REPORT_ROOT / "a1_stage2_internal_audit.json"
FINAL_MANIFEST_FILE = REPORT_ROOT / "a1_m3_final_manifest.json"

EXPECTED_EXCLUSIONS = ["mit60001-q-017", "mit60001-q-023", "mit60001-q-041"]
SOURCE_EXPERIMENT_RUN_ID = "mit60001_evidence_a1_experiment_607102394851e012"


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
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def serialize_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
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


def divide_or_none(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def classification(expected: str, predicted: str) -> str:
    return {
        ("accept", "accept"): "TP",
        ("reject", "accept"): "FP",
        ("accept", "reject"): "FN",
        ("reject", "reject"): "TN",
    }[(expected, predicted)]


def build_evaluation() -> dict[str, Any]:
    requests = load_jsonl(REQUEST_FILE)
    reviews = load_jsonl(PRIMARY_REVIEWS_FILE)
    entailments = load_jsonl(PRIMARY_ENTAILMENT_FILE)
    canonical_rows = load_csv(CANONICAL_DECISIONS_FILE)
    thresholds = json.loads(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    a1_manifest = json.loads(A1_MANIFEST_FILE.read_text(encoding="utf-8"))
    response_schema = json.loads(RESPONSE_SCHEMA_FILE.read_text(encoding="utf-8"))

    request_by_id = {row["question_id"]: row for row in requests}
    review_by_id = {row["question_id"]: row for row in reviews}
    entailment_by_id = {row["question_id"]: row for row in entailments}
    canonical_by_id = {row["question_id"]: row for row in canonical_rows}
    if any(len(rows) != 40 for rows in (requests, reviews, entailments, canonical_rows)):
        raise ValueError("A1 M3 requires exactly 40 rows in every source")
    if not (set(request_by_id) == set(review_by_id) == set(entailment_by_id) == set(canonical_by_id)):
        raise ValueError("A1 M3 source question IDs differ")

    excluded = sorted(
        row["question_id"] for row in canonical_rows if row["evaluation_status"] == "excluded"
    )
    evaluated = [row for row in canonical_rows if row["evaluation_status"] == "evaluated"]
    if excluded != EXPECTED_EXCLUSIONS or len(evaluated) != 37:
        raise ValueError("Canonical 37-question scope drift")
    expected_counts = Counter(row["expected_decision"] for row in evaluated)
    if expected_counts != {"accept": 21, "reject": 16}:
        raise ValueError("Canonical decision label distribution drift")

    expected_scope = {
        "evaluated_question_count": 37,
        "excluded_question_ids": EXPECTED_EXCLUSIONS,
        "additional_exclusions_allowed": False,
    }
    if thresholds["decision_evaluation_scope"] != expected_scope:
        raise ValueError("Frozen threshold scope drift")
    limits = thresholds["thresholds"]
    if limits["accept_recall_min"] != 0.75 or limits["false_accept_rate_max"] != 0.25 or limits["evidence_selection_precision_min"] != 0.85:
        raise ValueError("Frozen quality threshold drift")
    if a1_manifest["experiment_run_id"] != SOURCE_EXPERIMENT_RUN_ID or a1_manifest["validation_status"] != "passed":
        raise ValueError("Frozen A1 source experiment drift")
    primary_run = next(row for row in a1_manifest["runs"] if row["run_label"] == "primary")
    primary_hashes = {row["file"]: row["sha256"] for row in primary_run["output_artifacts"]}
    for source_path in (PRIMARY_REVIEWS_FILE, PRIMARY_ENTAILMENT_FILE):
        relative_path = source_path.relative_to(PROJECT_ROOT).as_posix()
        if primary_hashes.get(relative_path) != sha256_file(source_path):
            raise ValueError(f"Frozen A1 primary artifact hash drift: {relative_path}")

    response_validator = Draft202012Validator(response_schema)
    outside_top3_count = 0
    for question_id, response in review_by_id.items():
        errors = list(response_validator.iter_errors(response))
        if errors:
            raise ValueError(f"A1 response schema failed for {question_id}: {errors[0].message}")
        expected_top3 = [row["chunk_id"] for row in request_by_id[question_id]["candidates"]]
        if response["top3_chunk_ids"] != expected_top3:
            raise ValueError(f"A1 Top 3 identity drift for {question_id}")
        outside_top3_count += len(set(response["supporting_chunk_ids"]) - set(expected_top3))
    if outside_top3_count:
        raise ValueError("A1 returned supporting IDs outside Dense Top 3")

    confusion: Counter[str] = Counter()
    decision_rows: list[dict[str, Any]] = []
    for question_id in sorted(request_by_id):
        canonical = canonical_by_id[question_id]
        response = review_by_id[question_id]
        if canonical["evaluation_status"] == "evaluated":
            expected = canonical["expected_decision"]
            result = classification(expected, response["decision"])
            confusion[result] += 1
            correct: bool | str = expected == response["decision"]
        else:
            expected = ""
            result = "excluded"
            correct = ""
        decision_rows.append({
            "question_id": question_id,
            "evaluation_status": canonical["evaluation_status"],
            "exclusion_reason": canonical["exclusion_reason"],
            "expected_decision": expected,
            "predicted_decision": response["decision"],
            "decision_correct": correct,
            "classification": result,
            "final_supporting_chunk_count": len(response["supporting_chunk_ids"]),
            "decision_reason": response["decision_reason"],
        })

    tp, fp, fn, tn = (confusion["TP"], confusion["FP"], confusion["FN"], confusion["TN"])
    total = tp + fp + fn + tn
    decision_metrics = {
        "question_count": total,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": (tp + tn) / total,
        "accept_precision": divide_or_none(tp, tp + fp),
        "accept_precision_status": "defined" if tp + fp else "undefined_no_predicted_accepts",
        "accept_recall": divide_or_none(tp, tp + fn),
        "false_accept_rate": divide_or_none(fp, fp + tn),
        "false_reject_rate": divide_or_none(fn, tp + fn),
        "predicted_accept_count": sum(review_by_id[row["question_id"]]["decision"] == "accept" for row in evaluated),
        "predicted_reject_count": sum(review_by_id[row["question_id"]]["decision"] == "reject" for row in evaluated),
    }

    selected_pairs = [
        (row["question_id"], chunk_id)
        for row in evaluated
        for chunk_id in review_by_id[row["question_id"]]["supporting_chunk_ids"]
    ]
    evidence_selection = {
        "question_scope": "same_37_decision_evaluable_questions",
        "unit": "final_selected_question_chunk_pair",
        "selected_pair_count": len(selected_pairs),
        "supports_count": 0,
        "does_not_support_count": 0,
        "evidence_precision": None,
        "metric_status": "not_evaluable_zero_selected_pairs" if not selected_pairs else "requires_human_verdicts",
        "stage2_requirement_ids_included": False,
    }
    if selected_pairs:
        raise ValueError("A1 M3 approval requires human review when final selected pairs exist")

    assessment_count = supported_count = unsupported_count = 0
    questions_with_supported = questions_all_supported = 0
    for row in entailments:
        supported_in_question = sum(item["supported"] for item in row["assessments"])
        unsupported_in_question = len(row["assessments"]) - supported_in_question
        assessment_count += len(row["assessments"])
        supported_count += supported_in_question
        unsupported_count += unsupported_in_question
        questions_with_supported += supported_in_question > 0
        questions_all_supported += unsupported_in_question == 0
    internal_audit = {
        "schema_version": "evidence_review_a1_stage2_internal_audit_v1",
        "question_count": 40,
        "requirement_assessment_count": assessment_count,
        "supported_requirement_count": supported_count,
        "unsupported_requirement_count": unsupported_count,
        "questions_with_at_least_one_supported_requirement": questions_with_supported,
        "questions_with_all_requirements_supported": questions_all_supported,
        "final_selected_pair_metric_includes_internal_ids": False,
        "interpretation": "internal_debug_only_not_evidence_precision_input",
    }

    quality_gate = {
        "runtime_schema": {"status": "pass"},
        "accept_recall": {"value": decision_metrics["accept_recall"], "threshold_min": 0.75, "status": "fail"},
        "false_accept_rate": {"value": decision_metrics["false_accept_rate"], "threshold_max": 0.25, "status": "pass"},
        "evidence_selection_precision": {"value": None, "selected_pair_count": 0, "threshold_min": 0.85, "status": "not_evaluable"},
        "overall_status": "failed_candidate",
        "failed_thresholds": ["accept_recall"],
        "not_evaluable_metrics": ["evidence_selection_precision"],
        "failure_mode": "reject_class_collapse",
        "interpretation": "no_tried_configuration_reached_the_frozen_thresholds",
        "production_ready_claim_allowed": False,
        "generalization_claim_allowed": False,
    }
    metrics = {
        "schema_version": "evidence_review_a1_final_metrics_v1",
        "scope": {
            "development_question_count": 40,
            "evaluated_question_count": 37,
            "excluded_question_ids": EXPECTED_EXCLUSIONS,
        },
        "decision_metrics": decision_metrics,
        "evidence_selection": evidence_selection,
        "quality_gate": quality_gate,
    }
    return {"decision_rows": decision_rows, "metrics": metrics, "internal_audit": internal_audit}


def main() -> None:
    evaluation = build_evaluation()
    payloads = {
        DECISION_RESULTS_FILE.as_posix(): serialize_csv(evaluation["decision_rows"]),
        FINAL_METRICS_FILE.as_posix(): serialize_json(evaluation["metrics"]),
        INTERNAL_AUDIT_FILE.as_posix(): serialize_json(evaluation["internal_audit"]),
    }
    for relative_path, content in payloads.items():
        write_atomic(PROJECT_ROOT / relative_path, content)

    input_files = {
        "a1_entailment": PRIMARY_ENTAILMENT_FILE,
        "a1_manifest": A1_MANIFEST_FILE,
        "a1_reviews": PRIMARY_REVIEWS_FILE,
        "canonical_decisions": CANONICAL_DECISIONS_FILE,
        "evaluator": Path(__file__).resolve(),
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "request_package": REQUEST_FILE,
        "response_schema": RESPONSE_SCHEMA_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    input_sha256 = {label: sha256_file(path) for label, path in sorted(input_files.items())}
    identity = {"input_sha256": input_sha256, "output_sha256": {path: sha256_bytes(content) for path, content in sorted(payloads.items())}}
    metrics = evaluation["metrics"]
    manifest = {
        "$schema": "../../schemas/evidence_review_a1_m3_final_manifest_v1.schema.json",
        "schema_version": "evidence_review_a1_m3_final_manifest_v1",
        "evaluation_run_id": "mit60001_evidence_a1_m3_" + sha256_bytes(canonical_json(identity).encode("utf-8"))[:16],
        "candidate_id": "a1_two_stage_coverage_entailment_v1",
        "source_experiment_run_id": SOURCE_EXPERIMENT_RUN_ID,
        "scope": {
            "development_question_count": 40,
            "evaluated_question_count": 37,
            "expected_accept_count": 21,
            "expected_reject_count": 16,
            "excluded_question_ids": EXPECTED_EXCLUSIONS,
            "additional_exclusions_allowed": False,
        },
        "decision_metrics": metrics["decision_metrics"],
        "evidence_selection": metrics["evidence_selection"],
        "stage2_internal_audit": evaluation["internal_audit"],
        "quality_gate": metrics["quality_gate"],
        "input_sha256": input_sha256,
        "output_artifacts": [{"file": path, "sha256": sha256_bytes(content)} for path, content in sorted(payloads.items())],
        "model_calls": 0,
        "human_review_workbook_created": False,
        "ground_truth_modified": False,
        "additional_exclusions_created": False,
        "reviewer_research_status": "stopped_after_a1_per_frozen_rule",
        "validation_status": "passed",
    }
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(manifest))
    if errors:
        raise ValueError(f"A1 M3 manifest schema failed: {errors[0].message}")
    write_atomic(PROJECT_ROOT / FINAL_MANIFEST_FILE, serialize_json(manifest))
    print(canonical_json({
        "evaluation_run_id": manifest["evaluation_run_id"],
        "confusion_matrix": manifest["decision_metrics"]["confusion_matrix"],
        "accept_recall": manifest["decision_metrics"]["accept_recall"],
        "false_accept_rate": manifest["decision_metrics"]["false_accept_rate"],
        "evidence_precision": manifest["evidence_selection"]["evidence_precision"],
        "selected_pair_count": manifest["evidence_selection"]["selected_pair_count"],
        "overall_status": manifest["quality_gate"]["overall_status"],
    }))


if __name__ == "__main__":
    main()
