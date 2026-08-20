"""Đánh giá locked M2B outputs và tạo đầu vào human review cho M3.

Script không gọi LLM, không sửa Ground Truth và không biến 12 câu cần human
review thành nhãn giả. GT time overlap chỉ là tín hiệu audit, không phải kết luận
answer entailment.
"""

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

from src.evidence_review.prompts import PROMPT_VERSION, SYSTEM_PROMPT


CALIBRATION_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_calibration_v1.csv"
)
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
RESPONSE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)
GROUND_TRUTH_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
RUNTIME_MANIFEST_FILE = PROJECT_ROOT / (
    "reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json"
)
MANIFEST_SCHEMA_FILE = (
    PROJECT_ROOT / "schemas/evidence_reviewer_evaluation_manifest_v1.schema.json"
)

STRICT_RESULTS_FILE = Path(
    "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/strict_decision_results.csv"
)
STRICT_METRICS_FILE = Path(
    "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/strict_decision_metrics.json"
)
HUMAN_REVIEW_FILE = Path(
    "evaluation/review/evidence_accept_reject/m3_human_review_12_questions.csv"
)
EVIDENCE_AUDIT_FILE = Path(
    "evaluation/review/evidence_accept_reject/m3_accepted_evidence_audit.csv"
)
WORKBOOK_FILE = Path(
    "evaluation/review/evidence_accept_reject/outputs/phase8_m3/phase8_m3_evidence_reviewer_human_review.xlsx"
)
MANIFEST_FILE = Path(
    "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_pre_review_manifest.json"
)

EXPECTED_RUNTIME_RUN_ID = "mit60001_evidence_reviewer_0ee5e6a1362fc5c4"
EXPECTED_STRICT_COUNTS = {"strong_accept": 16, "strong_reject": 12}
EXPECTED_HUMAN_REVIEW_COUNT = 12
CONTEXT_LENGTH = 4096


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


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def overlaps_ground_truth(candidate: dict[str, Any], question: dict[str, Any]) -> bool:
    return any(
        candidate["video_id"] == time_range["video_id"]
        and float(candidate["start_second"]) < float(time_range["end_second"])
        and float(candidate["end_second"]) > float(time_range["start_second"])
        for time_range in question.get("relevant_time_ranges", [])
    )


def strict_classification(
    *, expected: str, predicted: str, answerable: bool
) -> str:
    if expected == "accept" and predicted == "accept":
        return "A_success_decision"
    if expected == "accept" and predicted == "reject":
        return "B_reviewer_false_reject"
    if expected == "reject" and predicted == "reject":
        return (
            "C_correct_abstention_retrieval_limit"
            if answerable
            else "out_of_scope_correct_reject"
        )
    return "D_potential_false_accept" if answerable else "out_of_scope_false_accept"


def safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def build(output_root: Path) -> dict[str, Any]:
    calibration = load_csv(CALIBRATION_FILE)
    requests = load_jsonl(REQUEST_FILE)
    responses = load_jsonl(RESPONSE_FILE)
    ground_truth = load_jsonl(GROUND_TRUTH_FILE)
    runtime_manifest = json.loads(RUNTIME_MANIFEST_FILE.read_text(encoding="utf-8"))

    calibration_by_id = {row["question_id"]: row for row in calibration}
    request_by_id = {row["question_id"]: row for row in requests}
    response_by_id = {row["question_id"]: row for row in responses}
    ground_truth_by_id = {row["question_id"]: row for row in ground_truth}
    expected_ids = set(calibration_by_id)
    if not (
        len(expected_ids) == 40
        and expected_ids == set(request_by_id)
        and expected_ids == set(response_by_id)
        and expected_ids == set(ground_truth_by_id)
    ):
        raise ValueError("M3 inputs must contain the same 40 unique question IDs")
    if runtime_manifest.get("runtime_run_id") != EXPECTED_RUNTIME_RUN_ID:
        raise ValueError("Locked M2B runtime_run_id mismatch")

    strict_rows: list[dict[str, Any]] = []
    human_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    confusion: Counter[tuple[str, str]] = Counter()

    for question_id in sorted(expected_ids):
        calibration_row = calibration_by_id[question_id]
        request = request_by_id[question_id]
        response = response_by_id[question_id]
        gt = ground_truth_by_id[question_id]
        expected_decision = calibration_row["reference_decision"]
        predicted_decision = response["decision"]
        answerable = gt["answerable"] is True
        candidates_by_id = {
            candidate["chunk_id"]: candidate for candidate in request["candidates"]
        }
        candidate_overlap = {
            candidate_id: overlaps_ground_truth(candidate, gt)
            for candidate_id, candidate in candidates_by_id.items()
        }

        if expected_decision:
            confusion[(expected_decision, predicted_decision)] += 1
            strict_rows.append(
                {
                    "question_id": question_id,
                    "question": gt["question"],
                    "answerable": answerable,
                    "calibration_class": calibration_row["calibration_class"],
                    "calibration_basis": calibration_row["calibration_basis"],
                    "expected_decision": expected_decision,
                    "predicted_decision": predicted_decision,
                    "decision_correct": expected_decision == predicted_decision,
                    "classification": strict_classification(
                        expected=expected_decision,
                        predicted=predicted_decision,
                        answerable=answerable,
                    ),
                    "supporting_chunk_ids": "\n".join(response["supporting_chunk_ids"]),
                    "decision_reason": response["decision_reason"],
                }
            )
        else:
            human_rows.append(
                {
                    "question_id": question_id,
                    "audit_flag": calibration_row["audit_flag"],
                    "credited_evidence_status": calibration_row["credited_evidence_status"],
                    "question": gt["question"],
                    "expected_answer_points": "\n".join(
                        f"- {point}" for point in gt.get("expected_answer_points", [])
                    ),
                    "relevant_time_ranges": canonical_json(gt.get("relevant_time_ranges", [])),
                    "model_decision": predicted_decision,
                    "model_reason": response["decision_reason"],
                    "model_supporting_chunk_ids": "\n".join(
                        response["supporting_chunk_ids"]
                    ),
                    "candidate_1": _candidate_review_text(request["candidates"][0], candidate_overlap),
                    "candidate_2": _candidate_review_text(request["candidates"][1], candidate_overlap),
                    "candidate_3": _candidate_review_text(request["candidates"][2], candidate_overlap),
                    "human_top3_sufficiency": "",
                    "human_reviewer_decision_correct": "",
                    "human_supporting_evidence_correct": "",
                    "human_final_classification": "",
                    "human_notes": "",
                    "human_review_status": "pending",
                }
            )

        if predicted_decision == "accept":
            for supporting_id in response["supporting_chunk_ids"]:
                candidate = candidates_by_id[supporting_id]
                evidence_rows.append(
                    {
                        "question_id": question_id,
                        "calibration_class": calibration_row["calibration_class"],
                        "question": gt["question"],
                        "expected_answer_points": "\n".join(
                            f"- {point}" for point in gt.get("expected_answer_points", [])
                        ),
                        "model_reason": response["decision_reason"],
                        "supporting_chunk_id": supporting_id,
                        "supporting_rank": candidate["rank"],
                        "supporting_chunk_text": candidate["chunk_text"],
                        "citation_url": candidate["citation_url"],
                        "auto_gt_time_overlap": candidate_overlap[supporting_id],
                        "human_entailment_verdict": "",
                        "human_notes": "",
                        "human_review_status": "pending",
                    }
                )

    strict_counts = Counter(row["calibration_class"] for row in strict_rows)
    if dict(strict_counts) != EXPECTED_STRICT_COUNTS:
        raise ValueError(f"Strict calibration count mismatch: {dict(strict_counts)}")
    if len(human_rows) != EXPECTED_HUMAN_REVIEW_COUNT:
        raise ValueError("Expected exactly 12 needs_human_review rows")
    audit_ids = {
        row["question_id"] for row in human_rows if row["audit_flag"]
    }
    if audit_ids != {"mit60001-q-023", "mit60001-q-041"}:
        raise ValueError("q-023/q-041 Ground Truth under-credit flags must be preserved")

    tp = confusion[("accept", "accept")]
    fp = confusion[("reject", "accept")]
    fn = confusion[("accept", "reject")]
    tn = confusion[("reject", "reject")]
    metrics = {
        "schema_version": "evidence_reviewer_strict_metrics_v1",
        "strict_question_count": len(strict_rows),
        "strong_accept_count": strict_counts["strong_accept"],
        "strong_reject_count": strict_counts["strong_reject"],
        "needs_human_review_count": len(human_rows),
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": safe_divide(tp + tn, tp + fp + fn + tn),
        "accept_precision": safe_divide(tp, tp + fp),
        "accept_recall": safe_divide(tp, tp + fn),
        "false_accept_rate": safe_divide(fp, fp + tn),
        "false_reject_rate": safe_divide(fn, tp + fn),
        "accepted_question_count": sum(
            response["decision"] == "accept" for response in responses
        ),
        "selected_supporting_chunk_count": len(evidence_rows),
        "selected_chunk_gt_overlap_count": sum(
            row["auto_gt_time_overlap"] for row in evidence_rows
        ),
        "evidence_entailment_status": "human_review_pending",
        "metric_scope_note": (
            "Decision metrics use only 28 strict calibration rows. GT time overlap is an "
            "audit signal, not proof of answer entailment."
        ),
    }

    strict_bytes = serialize_csv(strict_rows)
    human_bytes = serialize_csv(human_rows)
    evidence_bytes = serialize_csv(evidence_rows)
    metrics_bytes = (
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    output_payloads = {
        STRICT_RESULTS_FILE: strict_bytes,
        STRICT_METRICS_FILE: metrics_bytes,
        HUMAN_REVIEW_FILE: human_bytes,
        EVIDENCE_AUDIT_FILE: evidence_bytes,
    }
    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)

    input_files = {
        "calibration": CALIBRATION_FILE,
        "requests": REQUEST_FILE,
        "responses": RESPONSE_FILE,
        "ground_truth": GROUND_TRUTH_FILE,
        "runtime_manifest": RUNTIME_MANIFEST_FILE,
        "evaluation_script": Path(__file__).resolve(),
        "manifest_schema": MANIFEST_SCHEMA_FILE,
    }
    input_sha256 = {
        label: sha256_file(path) for label, path in sorted(input_files.items())
    }
    evaluation_run_id = "mit60001_evidence_reviewer_eval_" + sha256_bytes(
        canonical_json(input_sha256).encode("utf-8")
    )[:16]
    artifacts = [
        {"file": path.as_posix(), "sha256": sha256_bytes(content)}
        for path, content in output_payloads.items()
    ]
    workbook_path = output_root / WORKBOOK_FILE
    if workbook_path.exists():
        artifacts.append(
            {"file": WORKBOOK_FILE.as_posix(), "sha256": sha256_file(workbook_path)}
        )

    runtime = runtime_manifest["runtime"]
    execution = runtime_manifest["execution_config"]
    manifest = {
        "$schema": "../../schemas/evidence_reviewer_evaluation_manifest_v1.schema.json",
        "schema_version": "evidence_reviewer_evaluation_manifest_v1",
        "evaluation_run_id": evaluation_run_id,
        "locked_runtime_run_id": runtime_manifest["runtime_run_id"],
        "reproducibility_identity": {
            "provider": runtime_manifest["provider"],
            "ollama_version": runtime["ollama_version"],
            "model": runtime["model"],
            "model_digest": runtime["digest"],
            "quantization_level": runtime["quantization_level"],
            "temperature": execution["temperature"],
            "seed": execution["seed"],
            "num_predict": execution["num_predict"],
            "context_length": CONTEXT_LENGTH,
            "structured_output_schema_version": execution[
                "structured_output_schema_version"
            ],
            "prompt_version": PROMPT_VERSION,
            "system_prompt_sha256": sha256_bytes(SYSTEM_PROMPT.encode("utf-8")),
        },
        "strict_metrics": metrics,
        "human_review": {
            "question_count": len(human_rows),
            "accepted_question_count": metrics["accepted_question_count"],
            "selected_supporting_chunk_count": len(evidence_rows),
            "audit_flagged_question_ids": sorted(audit_ids),
            "status": "pending",
        },
        "input_sha256": input_sha256,
        "output_artifacts": artifacts,
        "validation_status": "passed",
        "m3_status": "human_review_pending",
    }
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    manifest_errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if manifest_errors:
        raise ValueError(f"M3 manifest schema failed: {manifest_errors[0].message}")
    write_atomic(
        output_root / MANIFEST_FILE,
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    return manifest


def _candidate_review_text(
    candidate: dict[str, Any], overlap_by_id: dict[str, bool]
) -> str:
    return (
        f"rank={candidate['rank']}\n"
        f"chunk_id={candidate['chunk_id']}\n"
        f"citation={candidate['citation_url']}\n"
        f"GT time overlap (audit signal only)={overlap_by_id[candidate['chunk_id']]}\n\n"
        f"{candidate['chunk_text']}"
    )


def main() -> None:
    manifest = build(PROJECT_ROOT)
    print(
        canonical_json(
            {
                "evaluation_run_id": manifest["evaluation_run_id"],
                "strict_metrics": manifest["strict_metrics"],
                "human_review": manifest["human_review"],
                "m3_status": manifest["m3_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
