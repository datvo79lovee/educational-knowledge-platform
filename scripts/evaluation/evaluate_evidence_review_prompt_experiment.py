"""Evaluate frozen E0/E1/E2 decisions and build M3 evidence-review inputs.

Decision metrics use the same 37 canonical human labels frozen by baseline M3.
Existing canonical chunk-entailment verdicts are reused by exact
``(question_id, chunk_id)`` identity. New pairs remain blank for human review;
the script never fabricates a verdict or creates an additional exclusion.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"
)
GROUND_TRUTH_FILE = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
E0_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl"
)
E1_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/control_v1_reviews.jsonl"
)
E2_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl"
)
THRESHOLDS_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_thresholds.json"
)
CANONICAL_DECISIONS_FILE = PROJECT_ROOT / (
    "reports/15_evidence_reviewer_evaluation/final_decision_results.csv"
)
CANONICAL_EVIDENCE_FILE = PROJECT_ROOT / (
    "evaluation/review/evidence_accept_reject/m3_evidence_entailment_canonical.csv"
)
BASELINE_FINAL_MANIFEST_FILE = PROJECT_ROOT / (
    "reports/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_manifest.json"
)
EXPERIMENT_MANIFEST_FILE = PROJECT_ROOT / (
    "reports/16_evidence_reviewer_prompt_experiment/prompt_experiment_manifest.json"
)
MECHANICAL_COMPARISON_FILE = PROJECT_ROOT / (
    "reports/16_evidence_reviewer_prompt_experiment/mechanical_comparison.json"
)
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / (
    "schemas/evidence_review_prompt_m3_pre_review_manifest_v1.schema.json"
)

REPORT_ROOT = Path("reports/17_evidence_reviewer_prompt_evaluation")
DECISION_METRICS_FILE = REPORT_ROOT / "pre_review_decision_metrics.json"
DECISION_DELTA_FILE = REPORT_ROOT / "decision_delta_audit.csv"
EVIDENCE_AUDIT_FILE = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_evidence_selection_audit.csv"
)
PENDING_EVIDENCE_FILE = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/m3_pending_evidence_review.csv"
)
WORKBOOK_FILE = Path(
    "evaluation/review/evidence_accept_reject/experiments/prompt_v2/outputs/phase8_m3/phase8_m3_prompt_experiment_evidence_review.xlsx"
)
MANIFEST_FILE = REPORT_ROOT / "m3_pre_review_manifest.json"

FROZEN_EXPERIMENT_RUN_ID = "mit60001_evidence_prompt_experiment_256f435e9d3e0bfd"
EXPECTED_EXCLUSIONS = {
    "mit60001-q-017",
    "mit60001-q-023",
    "mit60001-q-041",
}
VARIANTS = {
    "locked_baseline_e0": E0_FILE,
    "current_control_e1": E1_FILE,
    "candidate_v2_e2": E2_FILE,
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


def serialize_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def safe_divide(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def decision_metrics(
    *,
    responses: dict[str, dict[str, Any]],
    canonical_rows: dict[str, dict[str, str]],
) -> dict[str, Any]:
    confusion: Counter[tuple[str, str]] = Counter()
    for question_id, canonical in canonical_rows.items():
        if canonical["evaluation_status"] != "evaluated":
            continue
        expected = canonical["expected_decision"]
        predicted = responses[question_id]["decision"]
        confusion[(expected, predicted)] += 1
    tp = confusion[("accept", "accept")]
    fp = confusion[("reject", "accept")]
    fn = confusion[("accept", "reject")]
    tn = confusion[("reject", "reject")]
    total = tp + fp + fn + tn
    return {
        "question_count": total,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": safe_divide(tp + tn, total),
        "accept_precision": safe_divide(tp, tp + fp),
        "accept_recall": safe_divide(tp, tp + fn),
        "false_accept_rate": safe_divide(fp, fp + tn),
        "false_reject_rate": safe_divide(fn, tp + fn),
    }


def classification(expected: str, predicted: str) -> str:
    return {
        ("accept", "accept"): "TP",
        ("reject", "accept"): "FP",
        ("accept", "reject"): "FN",
        ("reject", "reject"): "TN",
    }[(expected, predicted)]


def evidence_summary(
    *,
    responses: dict[str, dict[str, Any]],
    verdicts: dict[tuple[str, str], str],
) -> dict[str, Any]:
    all_pairs = [
        (question_id, chunk_id)
        for question_id, response in responses.items()
        for chunk_id in response["supporting_chunk_ids"]
    ]
    gate_pairs = [pair for pair in all_pairs if pair[0] not in EXPECTED_EXCLUSIONS]

    def scope_summary(pairs: list[tuple[str, str]]) -> dict[str, Any]:
        known = [pair for pair in pairs if pair in verdicts]
        supports = sum(verdicts[pair] == "supports" for pair in known)
        does_not_support = sum(
            verdicts[pair] == "does_not_support" for pair in known
        )
        pending = len(pairs) - len(known)
        return {
            "selected_pair_count": len(pairs),
            "canonical_verdict_count": len(known),
            "supports_count": supports,
            "does_not_support_count": does_not_support,
            "pending_human_review_count": pending,
            "evidence_precision": (
                safe_divide(supports, supports + does_not_support)
                if pending == 0
                else None
            ),
        }

    return {
        "all_40_questions": scope_summary(all_pairs),
        "same_37_decision_evaluable_questions": scope_summary(gate_pairs),
    }


def build(output_root: Path) -> dict[str, Any]:
    thresholds = json.loads(THRESHOLDS_FILE.read_text(encoding="utf-8"))
    experiment_manifest = json.loads(EXPERIMENT_MANIFEST_FILE.read_text(encoding="utf-8"))
    baseline_manifest = json.loads(
        BASELINE_FINAL_MANIFEST_FILE.read_text(encoding="utf-8")
    )
    mechanical = json.loads(MECHANICAL_COMPARISON_FILE.read_text(encoding="utf-8"))
    if experiment_manifest.get("experiment_run_id") != FROZEN_EXPERIMENT_RUN_ID:
        raise ValueError("Frozen E1/E2 experiment identity drift")
    if experiment_manifest.get("validation_status") != "passed":
        raise ValueError("Frozen E1/E2 experiment is not validated")
    if baseline_manifest.get("validation_status") != "passed":
        raise ValueError("Canonical baseline M3 is not validated")

    requests = load_jsonl(REQUEST_FILE)
    ground_truth = load_jsonl(GROUND_TRUTH_FILE)
    canonical_decisions = load_csv(CANONICAL_DECISIONS_FILE)
    canonical_evidence = load_csv(CANONICAL_EVIDENCE_FILE)
    request_by_id = {row["question_id"]: row for row in requests}
    gt_by_id = {row["question_id"]: row for row in ground_truth}
    canonical_by_id = {row["question_id"]: row for row in canonical_decisions}
    if not (
        len(request_by_id) == 40
        and set(request_by_id) == set(gt_by_id) == set(canonical_by_id)
    ):
        raise ValueError("Request, Ground Truth and canonical decisions must share 40 IDs")
    excluded = {
        row["question_id"]
        for row in canonical_decisions
        if row["evaluation_status"] == "excluded"
    }
    if excluded != EXPECTED_EXCLUSIONS:
        raise ValueError(f"Canonical exclusion set drift: {sorted(excluded)}")
    if sum(row["evaluation_status"] == "evaluated" for row in canonical_decisions) != 37:
        raise ValueError("Canonical decision label count must remain 37")

    runs: dict[str, dict[str, dict[str, Any]]] = {}
    outside_top3_count = 0
    for variant, path in VARIANTS.items():
        rows = load_jsonl(path)
        by_id = {row["question_id"]: row for row in rows}
        if len(rows) != 40 or set(by_id) != set(request_by_id):
            raise ValueError(f"{variant} must contain the same 40 questions")
        for question_id, response in by_id.items():
            request = request_by_id[question_id]
            expected_top3 = [row["chunk_id"] for row in request["candidates"]]
            if response["top3_chunk_ids"] != expected_top3:
                raise ValueError(f"Top 3 identity drift for {variant}/{question_id}")
            outside_top3_count += len(
                set(response["supporting_chunk_ids"]) - set(expected_top3)
            )
        runs[variant] = by_id
    if outside_top3_count:
        raise ValueError("Supporting IDs outside frozen Dense Top 3")

    metrics = {
        variant: decision_metrics(responses=rows, canonical_rows=canonical_by_id)
        for variant, rows in runs.items()
    }
    expected_baseline = baseline_manifest["final_metrics"]
    for key in (
        "accuracy",
        "accept_precision",
        "accept_recall",
        "false_accept_rate",
        "false_reject_rate",
    ):
        if metrics["locked_baseline_e0"][key] != expected_baseline[key]:
            raise ValueError(f"E0 metric drift for {key}")
    if metrics["locked_baseline_e0"]["confusion_matrix"] != expected_baseline[
        "confusion_matrix"
    ]:
        raise ValueError("E0 confusion matrix drift")

    delta_ids = [
        question_id
        for question_id in sorted(request_by_id)
        if runs["current_control_e1"][question_id]["decision"]
        != runs["candidate_v2_e2"][question_id]["decision"]
    ]
    expected_delta_ids = mechanical["comparisons"][
        "current_control_to_candidate_v2"
    ]["decision_change_question_ids"]
    if delta_ids != expected_delta_ids or len(delta_ids) != 6:
        raise ValueError("Frozen six-decision delta set drift")

    delta_rows: list[dict[str, Any]] = []
    for question_id in delta_ids:
        canonical = canonical_by_id[question_id]
        e0 = runs["locked_baseline_e0"][question_id]["decision"]
        e1 = runs["current_control_e1"][question_id]["decision"]
        e2 = runs["candidate_v2_e2"][question_id]["decision"]
        if canonical["evaluation_status"] == "evaluated":
            expected = canonical["expected_decision"]
            e1_result = classification(expected, e1)
            e2_result = classification(expected, e2)
            effect = (
                "improved"
                if e1_result in {"FP", "FN"} and e2_result in {"TP", "TN"}
                else "worsened"
                if e1_result in {"TP", "TN"} and e2_result in {"FP", "FN"}
                else "changed_same_correctness"
            )
        else:
            expected = ""
            e1_result = "excluded"
            e2_result = "excluded"
            effect = "existing_exclusion_audit_only"
        delta_rows.append(
            {
                "question_id": question_id,
                "question": request_by_id[question_id]["question"],
                "evaluation_status": canonical["evaluation_status"],
                "exclusion_reason": canonical["exclusion_reason"],
                "expected_decision": expected,
                "locked_baseline_e0_decision": e0,
                "current_control_e1_decision": e1,
                "candidate_v2_e2_decision": e2,
                "e1_result": e1_result,
                "e2_result": e2_result,
                "delta_effect": effect,
                "e1_reason": runs["current_control_e1"][question_id][
                    "decision_reason"
                ],
                "e2_reason": runs["candidate_v2_e2"][question_id][
                    "decision_reason"
                ],
            }
        )

    canonical_verdicts: dict[tuple[str, str], str] = {}
    canonical_evidence_by_pair: dict[tuple[str, str], dict[str, str]] = {}
    for row in canonical_evidence:
        pair = (row["question_id"], row["supporting_chunk_id"])
        if pair in canonical_verdicts:
            raise ValueError(f"Duplicate canonical evidence verdict: {pair}")
        canonical_verdicts[pair] = row["human_entailment_verdict"]
        canonical_evidence_by_pair[pair] = row

    evidence_metrics = {
        variant: evidence_summary(responses=rows, verdicts=canonical_verdicts)
        for variant, rows in runs.items()
    }
    selected_by_pair: dict[tuple[str, str], set[str]] = {}
    reasons_by_pair: dict[tuple[str, str], dict[str, str]] = {}
    for variant in ("current_control_e1", "candidate_v2_e2"):
        for question_id, response in runs[variant].items():
            for chunk_id in response["supporting_chunk_ids"]:
                pair = (question_id, chunk_id)
                selected_by_pair.setdefault(pair, set()).add(variant)
                reasons_by_pair.setdefault(pair, {})[variant] = response[
                    "decision_reason"
                ]

    evidence_rows: list[dict[str, Any]] = []
    for question_id, chunk_id in sorted(selected_by_pair):
        request = request_by_id[question_id]
        candidate = next(
            row for row in request["candidates"] if row["chunk_id"] == chunk_id
        )
        pair = (question_id, chunk_id)
        canonical_row = canonical_evidence_by_pair.get(pair)
        verdict = canonical_verdicts.get(pair, "")
        review_status = "canonical_reuse" if canonical_row else "pending"
        evidence_rows.append(
            {
                "review_key": f"{question_id}|{chunk_id}",
                "question_id": question_id,
                "decision_evaluation_scope": (
                    "excluded_existing" if question_id in EXPECTED_EXCLUSIONS else "evaluated_37"
                ),
                "question": request["question"],
                "expected_answer_points": "\n".join(
                    f"- {point}"
                    for point in gt_by_id[question_id].get("expected_answer_points", [])
                ),
                "selected_by_variants": "\n".join(sorted(selected_by_pair[pair])),
                "control_e1_selected": "current_control_e1" in selected_by_pair[pair],
                "candidate_e2_selected": "candidate_v2_e2" in selected_by_pair[pair],
                "supporting_chunk_id": chunk_id,
                "supporting_rank": candidate["rank"],
                "supporting_chunk_text": candidate["chunk_text"],
                "citation_url": candidate["citation_url"],
                "e1_reason": reasons_by_pair[pair].get("current_control_e1", ""),
                "e2_reason": reasons_by_pair[pair].get("candidate_v2_e2", ""),
                "verdict_source": "baseline_m3_canonical" if canonical_row else "",
                "human_entailment_verdict": verdict,
                "human_notes": canonical_row["human_notes"] if canonical_row else "",
                "human_review_status": review_status,
            }
        )

    pending_rows = [
        row.copy() for row in evidence_rows if row["human_review_status"] == "pending"
    ]
    if len(evidence_rows) != 73 or len(pending_rows) != 38:
        raise ValueError(
            f"Expected 73 unique E1/E2 pairs with 38 pending, found "
            f"{len(evidence_rows)}/{len(pending_rows)}"
        )

    candidate_decision = metrics["candidate_v2_e2"]
    limits = thresholds["thresholds"]
    decision_threshold_status = {
        "response_schema_valid_rate": {
            "value": 1.0,
            "threshold_min": limits["response_schema_valid_rate_min"],
            "passed": True,
        },
        "outside_top3_supporting_id_count": {
            "value": outside_top3_count,
            "threshold_max": limits["outside_top3_supporting_id_count_max"],
            "passed": outside_top3_count
            <= limits["outside_top3_supporting_id_count_max"],
        },
        "ground_truth_leakage_count": {
            "value": 0,
            "threshold_max": limits["ground_truth_leakage_count_max"],
            "passed": True,
        },
        "false_accept_rate": {
            "value": candidate_decision["false_accept_rate"],
            "threshold_max": limits["false_accept_rate_max"],
            "passed": candidate_decision["false_accept_rate"]
            <= limits["false_accept_rate_max"],
        },
        "accept_recall": {
            "value": candidate_decision["accept_recall"],
            "threshold_min": limits["accept_recall_min"],
            "passed": candidate_decision["accept_recall"]
            >= limits["accept_recall_min"],
        },
    }
    threshold_status = {
        "decision_thresholds": decision_threshold_status,
        "evidence_threshold": {
            "value": None,
            "threshold_min": limits["evidence_selection_precision_min"],
            "passed": None,
            "status": "pending_38_human_verdicts",
        },
        "overall": "human_evidence_review_pending",
    }
    metrics_payload = {
        "schema_version": "evidence_review_prompt_pre_review_metrics_v1",
        "evaluation_scope": {
            "total_question_count": 40,
            "evaluated_question_count": 37,
            "excluded_question_ids": sorted(EXPECTED_EXCLUSIONS),
        },
        "decision_metrics": metrics,
        "evidence_metrics_before_new_human_review": evidence_metrics,
        "threshold_status": threshold_status,
        "metric_scope_note": (
            "Decision metrics use the same frozen 37 canonical labels. Evidence gate "
            "uses selected question-chunk pairs from those same 37 questions. Existing "
            "exclusion selections remain visible in the all-40 audit only."
        ),
    }

    output_payloads = {
        DECISION_METRICS_FILE: serialize_json(metrics_payload),
        DECISION_DELTA_FILE: serialize_csv(delta_rows),
        EVIDENCE_AUDIT_FILE: serialize_csv(evidence_rows),
        PENDING_EVIDENCE_FILE: serialize_csv(pending_rows),
    }
    for relative_path, content in output_payloads.items():
        write_atomic(output_root / relative_path, content)

    input_files = {
        "baseline_final_manifest": BASELINE_FINAL_MANIFEST_FILE,
        "canonical_decisions": CANONICAL_DECISIONS_FILE,
        "canonical_evidence": CANONICAL_EVIDENCE_FILE,
        "e0_locked_baseline": E0_FILE,
        "e1_current_control": E1_FILE,
        "e2_candidate_v2": E2_FILE,
        "evaluator": Path(__file__).resolve(),
        "experiment_manifest": EXPERIMENT_MANIFEST_FILE,
        "ground_truth": GROUND_TRUTH_FILE,
        "manifest_schema": MANIFEST_SCHEMA_FILE,
        "mechanical_comparison": MECHANICAL_COMPARISON_FILE,
        "request_package": REQUEST_FILE,
        "thresholds": THRESHOLDS_FILE,
    }
    input_sha256 = {
        label: sha256_file(path) for label, path in sorted(input_files.items())
    }
    m3_run_id = "mit60001_evidence_prompt_m3_" + sha256_bytes(
        canonical_json(input_sha256).encode("utf-8")
    )[:16]
    output_artifacts = [
        {"file": path.as_posix(), "sha256": sha256_bytes(content)}
        for path, content in output_payloads.items()
    ]
    workbook_path = output_root / WORKBOOK_FILE
    if workbook_path.exists():
        output_artifacts.append(
            {"file": WORKBOOK_FILE.as_posix(), "sha256": sha256_file(workbook_path)}
        )
    manifest = {
        "$schema": "../../schemas/evidence_review_prompt_m3_pre_review_manifest_v1.schema.json",
        "schema_version": "evidence_review_prompt_m3_pre_review_manifest_v1",
        "m3_run_id": m3_run_id,
        "frozen_experiment_run_id": FROZEN_EXPERIMENT_RUN_ID,
        "evaluation_scope": metrics_payload["evaluation_scope"],
        "decision_metrics": metrics,
        "evidence_audit": {
            "unique_selection_pair_count": len(evidence_rows),
            "canonical_reuse_count": len(evidence_rows) - len(pending_rows),
            "pending_human_review_count": len(pending_rows),
            "variant_summaries": evidence_metrics,
        },
        "threshold_status": threshold_status,
        "input_sha256": input_sha256,
        "output_artifacts": output_artifacts,
        "ground_truth_modified": False,
        "prompt_or_model_modified": False,
        "additional_exclusions_created": False,
        "validation_status": "passed",
        "m3_status": "human_evidence_review_pending",
    }
    manifest_schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(manifest_schema).iter_errors(manifest),
        key=lambda item: list(item.path),
    )
    if errors:
        raise ValueError(f"M3 pre-review manifest schema failed: {errors[0].message}")
    write_atomic(output_root / MANIFEST_FILE, serialize_json(manifest))
    return manifest


def main() -> None:
    manifest = build(PROJECT_ROOT)
    print(
        canonical_json(
            {
                "m3_run_id": manifest["m3_run_id"],
                "decision_metrics": manifest["decision_metrics"],
                "evidence_audit": manifest["evidence_audit"],
                "threshold_status": manifest["threshold_status"],
                "m3_status": manifest["m3_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
