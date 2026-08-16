"""Canonicalize completed M3 human review and calculate final reviewer metrics.

Input JSON phải là bản export máy đọc từ workbook reviewed. Script kiểm tra toàn
bộ immutable columns với package gốc trước khi nhận các cột human decision.
"""

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
CALIBRATION_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/evidence_review_calibration_v1.csv"
PENDING_HUMAN_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/m3_human_review_12_questions.csv"
PENDING_EVIDENCE_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/m3_accepted_evidence_audit.csv"
STRICT_RESULTS_FILE = PROJECT_ROOT / "reports/15_evidence_reviewer_evaluation/strict_decision_results.csv"
RUNTIME_MANIFEST_FILE = PROJECT_ROOT / "reports/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
FINAL_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_reviewer_evaluation_final_manifest_v1.schema.json"

CANONICAL_HUMAN_FILE = Path("evaluation/review/evidence_accept_reject/m3_human_review_12_canonical.csv")
CANONICAL_EVIDENCE_FILE = Path("evaluation/review/evidence_accept_reject/m3_evidence_entailment_canonical.csv")
FINAL_RESULTS_FILE = Path("reports/15_evidence_reviewer_evaluation/final_decision_results.csv")
FINAL_METRICS_FILE = Path("reports/15_evidence_reviewer_evaluation/final_metrics.json")
FINAL_MANIFEST_FILE = Path("reports/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_manifest.json")

VALID_SUFFICIENCY = {"sufficient", "insufficient", "possible_gt_under_credit", "needs_discussion"}
VALID_CORRECTNESS = {"yes", "no", "needs_discussion"}
VALID_SUPPORT_CORRECTNESS = {"yes", "no", "not_applicable", "needs_discussion"}
VALID_CLASSIFICATIONS = {
    "A_success",
    "B_reviewer_false_reject",
    "C_correct_abstention",
    "D_potential_false_accept",
    "benchmark_gt_issue",
    "needs_discussion",
}
VALID_ENTAILMENT = {"supports", "does_not_support"}
EXPECTED_EXCLUDED_IDS = {"mit60001-q-017", "mit60001-q-023", "mit60001-q-041"}
EXPECTED_GT_ISSUE_IDS = {"mit60001-q-023", "mit60001-q-041"}


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


def serialize_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("Cannot serialize empty CSV")
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


def require_exact_ids(rows: list[dict[str, Any]], expected: set[str], label: str) -> None:
    actual = [str(row["question_id"]) for row in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError(f"{label} question IDs do not match expected set")


def expected_from_sufficiency(value: str) -> str | None:
    if value == "sufficient":
        return "accept"
    if value == "insufficient":
        return "reject"
    return None


def expected_classification(expected: str, predicted: str) -> str:
    mapping = {
        ("accept", "accept"): "A_success",
        ("accept", "reject"): "B_reviewer_false_reject",
        ("reject", "reject"): "C_correct_abstention",
        ("reject", "accept"): "D_potential_false_accept",
    }
    return mapping[(expected, predicted)]


def safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def build(review_export: Path, output_root: Path) -> dict[str, Any]:
    raw_bytes = review_export.read_bytes()
    export = json.loads(raw_bytes.decode("utf-8"))
    human_rows = export.get("humanRows")
    evidence_rows = export.get("evidenceRows")
    workbook_sha256 = export.get("workbookSha256")
    if not isinstance(human_rows, list) or not isinstance(evidence_rows, list):
        raise ValueError("Review export must contain humanRows and evidenceRows")
    if not isinstance(workbook_sha256, str) or len(workbook_sha256) != 64:
        raise ValueError("Review export must contain reviewed workbook SHA-256")

    pending_human = load_csv(PENDING_HUMAN_FILE)
    pending_evidence = load_csv(PENDING_EVIDENCE_FILE)
    strict_rows = load_csv(STRICT_RESULTS_FILE)
    calibration = load_csv(CALIBRATION_FILE)
    expected_human_ids = {row["question_id"] for row in pending_human}
    require_exact_ids(human_rows, expected_human_ids, "Human review")
    if len(evidence_rows) != 35:
        raise ValueError("Evidence review must contain exactly 35 rows")

    pending_human_by_id = {row["question_id"]: row for row in pending_human}
    immutable_human_fields = (
        "question_id",
        "audit_flag",
        "credited_evidence_status",
        "question",
        "expected_answer_points",
        "relevant_time_ranges",
        "model_decision",
        "model_reason",
        "model_supporting_chunk_ids",
        "candidate_1",
        "candidate_2",
        "candidate_3",
    )
    canonical_human: list[dict[str, Any]] = []
    for row in sorted(human_rows, key=lambda item: str(item["question_id"])):
        question_id = str(row["question_id"])
        source = pending_human_by_id[question_id]
        for field in immutable_human_fields:
            if str(row.get(field, "")) != str(source.get(field, "")):
                raise ValueError(f"Immutable human-review field changed: {question_id}.{field}")
        if row.get("human_review_status") != "reviewed":
            raise ValueError(f"Human review is not completed: {question_id}")
        sufficiency = str(row.get("human_top3_sufficiency", ""))
        correctness = str(row.get("human_reviewer_decision_correct", ""))
        support_correctness = str(row.get("human_supporting_evidence_correct", ""))
        classification = str(row.get("human_final_classification", ""))
        if sufficiency not in VALID_SUFFICIENCY:
            raise ValueError(f"Invalid sufficiency for {question_id}: {sufficiency}")
        if correctness not in VALID_CORRECTNESS:
            raise ValueError(f"Invalid decision correctness for {question_id}: {correctness}")
        if support_correctness not in VALID_SUPPORT_CORRECTNESS:
            raise ValueError(f"Invalid support correctness for {question_id}: {support_correctness}")
        if classification not in VALID_CLASSIFICATIONS:
            raise ValueError(f"Invalid final classification for {question_id}: {classification}")

        predicted = str(row["model_decision"])
        expected = expected_from_sufficiency(sufficiency)
        if expected is not None:
            required_correctness = "yes" if predicted == expected else "no"
            required_classification = expected_classification(expected, predicted)
            if correctness != required_correctness or classification != required_classification:
                raise ValueError(f"Inconsistent adjudication fields for {question_id}")
        elif question_id in EXPECTED_GT_ISSUE_IDS:
            if sufficiency != "possible_gt_under_credit" or classification != "benchmark_gt_issue":
                raise ValueError(f"GT issue classification lost for {question_id}")
        elif question_id == "mit60001-q-017":
            if sufficiency != "needs_discussion" or classification != "needs_discussion":
                raise ValueError("q-017 must remain needs_discussion")
        canonical_human.append({**row, "source_workbook_sha256": workbook_sha256})

    evidence_key = lambda row: (str(row["question_id"]), str(row["supporting_chunk_id"]))
    pending_evidence_by_key = {evidence_key(row): row for row in pending_evidence}
    if len(pending_evidence_by_key) != 35:
        raise ValueError("Pending evidence package contains duplicate keys")
    immutable_evidence_fields = (
        "question_id",
        "calibration_class",
        "question",
        "expected_answer_points",
        "model_reason",
        "supporting_chunk_id",
        "supporting_rank",
        "supporting_chunk_text",
        "citation_url",
        "auto_gt_time_overlap",
    )
    canonical_evidence: list[dict[str, Any]] = []
    verdicts_by_question: dict[str, list[str]] = {}
    for row in sorted(evidence_rows, key=evidence_key):
        key = evidence_key(row)
        if key not in pending_evidence_by_key:
            raise ValueError(f"Unexpected reviewed evidence key: {key}")
        source = pending_evidence_by_key[key]
        for field in immutable_evidence_fields:
            if str(row.get(field, "")) != str(source.get(field, "")):
                raise ValueError(f"Immutable evidence field changed: {key}.{field}")
        if row.get("human_review_status") != "reviewed":
            raise ValueError(f"Evidence review is not completed: {key}")
        verdict = str(row.get("human_entailment_verdict", ""))
        if verdict not in VALID_ENTAILMENT:
            raise ValueError(f"Invalid entailment verdict for {key}: {verdict}")
        verdicts_by_question.setdefault(key[0], []).append(verdict)
        canonical_evidence.append({**row, "source_workbook_sha256": workbook_sha256})

    for row in canonical_human:
        if row["model_decision"] != "accept":
            continue
        verdicts = verdicts_by_question.get(row["question_id"], [])
        expected_support = "yes" if verdicts and all(v == "supports" for v in verdicts) else "no"
        if row["human_supporting_evidence_correct"] != expected_support:
            raise ValueError(f"Supporting-evidence summary mismatch for {row['question_id']}")

    calibration_by_id = {row["question_id"]: row for row in calibration}
    final_rows: list[dict[str, Any]] = []
    for row in strict_rows:
        answerable = str(row["answerable"]).lower() == "true"
        classification = row["classification"]
        normalized = {
            "A_success_decision": "A_success",
            "B_reviewer_false_reject": "B_reviewer_false_reject",
            "C_correct_abstention_retrieval_limit": "C_correct_abstention",
            "D_potential_false_accept": "D_potential_false_accept",
            "out_of_scope_correct_reject": "out_of_scope_correct_reject",
        }[classification]
        retrieval_sufficiency = (
            "out_of_scope"
            if not answerable
            else ("sufficient" if row["expected_decision"] == "accept" else "insufficient")
        )
        final_rows.append(
            {
                "question_id": row["question_id"],
                "label_source": "strict_calibration",
                "evaluation_status": "evaluated",
                "retrieval_sufficiency": retrieval_sufficiency,
                "expected_decision": row["expected_decision"],
                "predicted_decision": row["predicted_decision"],
                "decision_correct": row["decision_correct"],
                "final_classification": normalized,
                "exclusion_reason": "",
            }
        )
    for row in canonical_human:
        expected = expected_from_sufficiency(row["human_top3_sufficiency"])
        excluded = expected is None
        final_rows.append(
            {
                "question_id": row["question_id"],
                "label_source": "human_adjudication",
                "evaluation_status": "excluded" if excluded else "evaluated",
                "retrieval_sufficiency": row["human_top3_sufficiency"],
                "expected_decision": expected or "",
                "predicted_decision": row["model_decision"],
                "decision_correct": "" if excluded else row["human_reviewer_decision_correct"] == "yes",
                "final_classification": row["human_final_classification"],
                "exclusion_reason": row["human_final_classification"] if excluded else "",
            }
        )
    final_rows.sort(key=lambda item: item["question_id"])
    excluded_ids = {row["question_id"] for row in final_rows if row["evaluation_status"] == "excluded"}
    if excluded_ids != EXPECTED_EXCLUDED_IDS:
        raise ValueError(f"Unexpected final exclusion set: {sorted(excluded_ids)}")

    evaluated = [row for row in final_rows if row["evaluation_status"] == "evaluated"]
    confusion = Counter((row["expected_decision"], row["predicted_decision"]) for row in evaluated)
    tp = confusion[("accept", "accept")]
    fp = confusion[("reject", "accept")]
    fn = confusion[("accept", "reject")]
    tn = confusion[("reject", "reject")]
    verdict_counts = Counter(row["human_entailment_verdict"] for row in canonical_evidence)
    class_counts = Counter(row["final_classification"] for row in final_rows)
    final_metrics = {
        "schema_version": "evidence_reviewer_final_metrics_v1",
        "total_question_count": 40,
        "evaluated_question_count": len(evaluated),
        "excluded_question_count": len(excluded_ids),
        "excluded_question_ids": sorted(excluded_ids),
        "ground_truth_issue_question_ids": sorted(EXPECTED_GT_ISSUE_IDS),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": safe_divide(tp + tn, len(evaluated)),
        "accept_precision": safe_divide(tp, tp + fp),
        "accept_recall": safe_divide(tp, tp + fn),
        "false_accept_rate": safe_divide(fp, fp + tn),
        "false_reject_rate": safe_divide(fn, tp + fn),
        "classification_counts": dict(sorted(class_counts.items())),
        "selected_supporting_chunk_count": len(canonical_evidence),
        "supporting_chunk_count": verdict_counts["supports"],
        "non_supporting_chunk_count": verdict_counts["does_not_support"],
        "evidence_selection_precision": safe_divide(
            verdict_counts["supports"], len(canonical_evidence)
        ),
        "human_review_status": "complete",
        "metric_scope_note": (
            "Decision metrics use 28 strict rows plus 9 human-adjudicated rows. "
            "q-017, q-023 and q-041 are excluded rather than forced into labels."
        ),
    }

    output_payloads = {
        CANONICAL_HUMAN_FILE: serialize_csv(canonical_human),
        CANONICAL_EVIDENCE_FILE: serialize_csv(canonical_evidence),
        FINAL_RESULTS_FILE: serialize_csv(final_rows),
        FINAL_METRICS_FILE: (
            json.dumps(final_metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
    }
    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)

    runtime_manifest = json.loads(RUNTIME_MANIFEST_FILE.read_text(encoding="utf-8"))
    input_sha256 = {
        "calibration": sha256_file(CALIBRATION_FILE),
        "pending_human_package": sha256_file(PENDING_HUMAN_FILE),
        "pending_evidence_package": sha256_file(PENDING_EVIDENCE_FILE),
        "strict_results": sha256_file(STRICT_RESULTS_FILE),
        "runtime_manifest": sha256_file(RUNTIME_MANIFEST_FILE),
        "canonicalizer": sha256_file(Path(__file__).resolve()),
        "final_manifest_schema": sha256_file(FINAL_SCHEMA_FILE),
        "review_export": sha256_bytes(raw_bytes),
        "reviewed_workbook": workbook_sha256,
    }
    final_run_id = "mit60001_evidence_reviewer_final_" + sha256_bytes(
        canonical_json(input_sha256).encode("utf-8")
    )[:16]
    manifest = {
        "$schema": "../../schemas/evidence_reviewer_evaluation_final_manifest_v1.schema.json",
        "schema_version": "evidence_reviewer_evaluation_final_manifest_v1",
        "final_run_id": final_run_id,
        "locked_runtime_run_id": runtime_manifest["runtime_run_id"],
        "reviewed_workbook": {
            "file": "evaluation/review/evidence_accept_reject/outputs/phase8_m3/phase8_m3_evidence_reviewer_human_review_reviewed.xlsx",
            "sha256": workbook_sha256,
        },
        "final_metrics": final_metrics,
        "input_sha256": input_sha256,
        "output_artifacts": [
            {"file": path.as_posix(), "sha256": sha256_bytes(content)}
            for path, content in output_payloads.items()
        ],
        "ground_truth_modified": False,
        "prompt_or_model_modified": False,
        "validation_status": "passed",
        "m3_status": "complete_with_exclusions",
    }
    schema = json.loads(FINAL_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        raise ValueError(f"Final M3 manifest schema failed: {errors[0].message}")
    write_atomic(
        output_root / FINAL_MANIFEST_FILE,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-export", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build(args.review_export.resolve(), args.output_root.resolve())
    print(canonical_json({"final_run_id": manifest["final_run_id"], "final_metrics": manifest["final_metrics"], "m3_status": manifest["m3_status"]}))


if __name__ == "__main__":
    main()

