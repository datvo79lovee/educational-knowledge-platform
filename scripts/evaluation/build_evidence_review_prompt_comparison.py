"""Build mechanical E0/E1/E2 comparison without reading Ground Truth."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
LOCKED_BASELINE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)
CONTROL_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/control_v1_reviews.jsonl"
)
CANDIDATE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl"
)
DELTA_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/decision_deltas.csv"
)
COMPARISON_FILE = PROJECT_ROOT / (
    "reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/mechanical_comparison.json"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


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


def comparison(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    question_ids = sorted(left)
    if set(question_ids) != set(right):
        raise ValueError("Comparison inputs have different question IDs")
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
    requests = {row["question_id"]: row for row in load_jsonl(REQUEST_FILE)}
    baseline = {row["question_id"]: row for row in load_jsonl(LOCKED_BASELINE_FILE)}
    control = {row["question_id"]: row for row in load_jsonl(CONTROL_FILE)}
    candidate = {row["question_id"]: row for row in load_jsonl(CANDIDATE_FILE)}
    if not (len(requests) == 40 and set(requests) == set(baseline) == set(control) == set(candidate)):
        raise ValueError("E0/E1/E2 inputs must contain the same 40 questions")

    rows: list[dict[str, Any]] = []
    for question_id in sorted(requests):
        request = requests[question_id]
        expected_top3 = [row["chunk_id"] for row in request["candidates"]]
        if any(
            run[question_id]["top3_chunk_ids"] != expected_top3
            for run in (baseline, control, candidate)
        ):
            raise ValueError(f"Top 3 identity drift for {question_id}")
        rows.append(
            {
                "question_id": question_id,
                "question": request["question"],
                "locked_baseline_decision": baseline[question_id]["decision"],
                "current_control_decision": control[question_id]["decision"],
                "candidate_v2_decision": candidate[question_id]["decision"],
                "baseline_to_control_decision_changed": baseline[question_id]["decision"]
                != control[question_id]["decision"],
                "control_to_candidate_decision_changed": control[question_id]["decision"]
                != candidate[question_id]["decision"],
                "locked_baseline_supporting_chunk_ids": json.dumps(
                    baseline[question_id]["supporting_chunk_ids"], separators=(",", ":")
                ),
                "current_control_supporting_chunk_ids": json.dumps(
                    control[question_id]["supporting_chunk_ids"], separators=(",", ":")
                ),
                "candidate_v2_supporting_chunk_ids": json.dumps(
                    candidate[question_id]["supporting_chunk_ids"], separators=(",", ":")
                ),
            }
        )

    delta_bytes = serialize_csv(rows)
    inputs = {
        "request_package": REQUEST_FILE,
        "locked_baseline": LOCKED_BASELINE_FILE,
        "current_control": CONTROL_FILE,
        "candidate_v2": CANDIDATE_FILE,
        "builder": Path(__file__).resolve(),
    }
    result = {
        "schema_version": "evidence_review_prompt_mechanical_comparison_v1",
        "comparison_scope": "decisions_and_supporting_ids_without_ground_truth",
        "input_sha256": {
            label: sha256_file(path) for label, path in sorted(inputs.items())
        },
        "comparisons": {
            "locked_baseline_to_current_control": comparison(baseline, control),
            "current_control_to_candidate_v2": comparison(control, candidate),
        },
        "output_artifacts": [
            {"file": relative(DELTA_FILE), "sha256": sha256_bytes(delta_bytes)}
        ],
        "ground_truth_read": False,
        "validation_status": "passed",
    }
    write_atomic(DELTA_FILE, delta_bytes)
    write_atomic(
        COMPARISON_FILE,
        (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
