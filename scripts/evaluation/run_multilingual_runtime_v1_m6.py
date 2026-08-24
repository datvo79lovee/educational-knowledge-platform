"""Prepare and evaluate the frozen M5.3 Vietnamese quality-review worksheet.

M6 is read-only with respect to runtime: it never calls Ollama, reruns retrieval, or
changes Ground Truth. ``--prepare`` writes a blind worksheet from frozen M5.3 output.
``--evaluate`` consumes the reviewed copy only after all protocol and protected-column
checks pass. ``--verify-only`` writes nothing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.run_multilingual_runtime_v1_m3 import (  # noqa: E402
    deterministic_intent_order,
    wilson_interval,
)


REPORT_DIR = PROJECT_ROOT / "reports/35_multilingual_runtime_v1_m6"
PREREGISTRATION = REPORT_DIR / "m6_preregistration.json"
M5_OUTPUTS = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3/m5_3_runtime_outputs.jsonl"
M5_FINAL_MANIFEST = PROJECT_ROOT / "reports/34_multilingual_runtime_v1_m5_3/m5_3_final_manifest.json"
QUESTIONS = PROJECT_ROOT / "evaluation/mit_60001/evaluation_questions.jsonl"
GOLD = PROJECT_ROOT / "data/gold/mit_60001/chunks.jsonl"
WORKSHEET = REPORT_DIR / "m6_human_review_worksheet.csv"
REVIEWED_WORKSHEET = REPORT_DIR / "m6_human_review_worksheet_reviewed.csv"
PREPARATION_MANIFEST = REPORT_DIR / "m6_preparation_manifest.json"
FINAL_RESULTS = REPORT_DIR / "m6_final_results.csv"
METRICS = REPORT_DIR / "m6_metrics.json"
EVALUATION_MANIFEST = REPORT_DIR / "m6_evaluation_manifest.json"

EXPECTED_INTENT_COUNT = 20
PRIMARY_EXCLUDED_IDS = {"mit60001-q-023"}
REVIEW_ORDER_SEED = "6000106"
DECISION_MINIMUM = 10
STRICT_E2E_MINIMUM = 6

PROTECTED_FIELDS = (
    "intent_id",
    "evaluation_scope",
    "question_vi",
    "expected_answer_points_json",
    "top3_evidence_json",
    "decision",
    "answer",
    "selected_citations_json",
    "runtime_status",
)
REVIEW_FIELDS = (
    "evidence_sufficiency",
    "decision_judgment",
    "answer_correctness",
    "answer_completeness",
    "groundedness",
    "citation_support_overall",
    "output_language",
    "reviewer_notes",
)
WORKSHEET_FIELDS = PROTECTED_FIELDS + REVIEW_FIELDS
DERIVED_FIELDS = (
    "decision_correct",
    "language_compliant",
    "strict_answer_success",
    "strict_end_to_end_success",
    "failure_reason",
)

ALLOWED = {
    "evidence_sufficiency": {"Sufficient", "Insufficient"},
    "decision_judgment": {"Correct", "Incorrect"},
    "answer_correctness": {"Correct", "Partial", "Incorrect", "N/A"},
    "answer_completeness": {"Complete", "Partial", "Incomplete", "N/A"},
    "groundedness": {"Grounded", "Partial", "Ungrounded", "N/A"},
    "citation_support_overall": {"All support", "Partial support", "None support", "N/A"},
    "output_language": {"Vietnamese", "Mixed technical terms acceptable", "Not Vietnamese", "N/A"},
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline=None) as handle:
        normalized = handle.read().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return tuple(reader.fieldnames or ()), rows


def serialize_csv(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    write_atomic(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def verify_hash_map(values: dict[str, str], *, lf: bool, label: str) -> None:
    if not values:
        raise ValueError(f"M6 pre-registration has no {label} pins")
    mismatches = []
    for relative_path, expected in values.items():
        path = PROJECT_ROOT / relative_path
        actual = sha256_file_lf(path) if lf else sha256_file(path)
        if actual != expected:
            mismatches.append(relative_path)
    if mismatches:
        raise ValueError(f"{label} changed since M6 pre-registration: " + ", ".join(mismatches))


def verify_preregistration() -> dict[str, Any]:
    prereg = load_json(PREREGISTRATION)
    if prereg["status"] != "preregistered_not_reviewed":
        raise ValueError("M6 pre-registration is not in the pre-review state")
    verify_hash_map(prereg["frozen_inputs_sha256"], lf=False, label="Frozen input")
    verify_hash_map(prereg["analysis_code_sha256_lf_normalized"], lf=True, label="Analysis code")
    final = load_json(M5_FINAL_MANIFEST)
    if final["status"] != "frozen_passed_runtime_gates":
        raise ValueError("M5.3 is not frozen as a passing runtime-gate attempt")
    if final["candidate_decision"] != "ADVANCE_TO_M6_QUALITY_EVALUATION":
        raise ValueError("M5.3 does not authorize M6 quality evaluation")
    return prereg


def build_worksheet_rows(prereg: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = load_jsonl(M5_OUTPUTS)
    questions = {str(row["question_id"]): row for row in load_jsonl(QUESTIONS)}
    chunks = {str(row["chunk_id"]): row for row in load_jsonl(GOLD)}
    if len(outputs) != EXPECTED_INTENT_COUNT or any(row["runtime_status"] != "passed" for row in outputs):
        raise ValueError("M6 requires the frozen complete 20/20 M5.3 output")
    if len({row["intent_id"] for row in outputs}) != EXPECTED_INTENT_COUNT:
        raise ValueError("M5.3 output has duplicate intent IDs")

    output_by_id = {str(row["intent_id"]): row for row in outputs}
    selected_ids = set(prereg["evaluation_scope"]["selected_intent_ids"])
    if set(output_by_id) != selected_ids:
        raise ValueError("M5.3 intent IDs differ from the M6 pre-registered set")
    ordered_ids = deterministic_intent_order(list(output_by_id), REVIEW_ORDER_SEED)
    if ordered_ids != prereg["human_review"]["worksheet_order"]["expected_intent_order"]:
        raise ValueError("M6 worksheet order differs from pre-registration")

    rows: list[dict[str, Any]] = []
    for intent_id in ordered_ids:
        output = output_by_id[intent_id]
        question = questions[intent_id]
        top3 = [
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "excerpt": chunks[chunk_id]["chunk_text"],
            }
            for rank, chunk_id in enumerate(output["top3_chunk_ids"], start=1)
        ]
        selected_ids = set(output["supporting_chunk_ids"])
        selected = [row for row in top3 if row["chunk_id"] in selected_ids]
        rows.append({
            "intent_id": intent_id,
            "evaluation_scope": (
                "excluded_frozen_ground_truth_ambiguity"
                if intent_id in PRIMARY_EXCLUDED_IDS else "primary"
            ),
            "question_vi": output["original_query"],
            "expected_answer_points_json": canonical_json(question["expected_answer_points"]),
            "top3_evidence_json": canonical_json(top3),
            "decision": output["decision"],
            "answer": output["answer"] or "",
            "selected_citations_json": canonical_json(selected),
            "runtime_status": output["runtime_status"],
            **{field: "" for field in REVIEW_FIELDS},
        })
    return rows


def prepare(prereg: dict[str, Any]) -> None:
    if WORKSHEET.exists() or PREPARATION_MANIFEST.exists():
        raise FileExistsError("M6 preparation artifacts already exist")
    rows = build_worksheet_rows(prereg)
    write_atomic(WORKSHEET, serialize_csv(rows, WORKSHEET_FIELDS))
    manifest = {
        "schema_version": "multilingual_runtime_v1_m6_preparation_manifest_v1",
        "milestone": "multilingual_runtime_v1_m6",
        "status": "prepared_awaiting_human_review",
        "preregistration": {
            "file": str(PREREGISTRATION.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(PREREGISTRATION),
        },
        "worksheet": {
            "file": str(WORKSHEET.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha256_file(WORKSHEET),
            "encoding": "UTF-8 with BOM",
            "row_count": len(rows),
            "primary_count": sum(row["evaluation_scope"] == "primary" for row in rows),
            "excluded_count": sum(row["evaluation_scope"] != "primary" for row in rows),
        },
        "runtime_calls": 0,
        "review_labels_present": False,
        "quality_metrics_computed": False,
    }
    write_json(PREPARATION_MANIFEST, manifest)


def validate_reviewed_rows(
    prereg: dict[str, Any], canonical_rows: list[dict[str, str]], reviewed_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    if len(canonical_rows) != EXPECTED_INTENT_COUNT or len(reviewed_rows) != EXPECTED_INTENT_COUNT:
        raise ValueError("M6 canonical and reviewed worksheets must both contain 20 rows")
    evaluated: list[dict[str, Any]] = []
    for canonical, reviewed in zip(canonical_rows, reviewed_rows, strict=True):
        intent_id = canonical["intent_id"]
        for field in PROTECTED_FIELDS:
            if reviewed.get(field) != canonical[field]:
                raise ValueError(f"Protected M6 field changed for {intent_id}: {field}")
        for field, allowed in ALLOWED.items():
            if reviewed.get(field) not in allowed:
                raise ValueError(f"Invalid or missing M6 label for {intent_id}: {field}")

        decision = reviewed["decision"]
        evidence_sufficient = reviewed["evidence_sufficiency"] == "Sufficient"
        decision_correct = (decision == "answer") == evidence_sufficient
        expected_judgment = "Correct" if decision_correct else "Incorrect"
        if reviewed["decision_judgment"] != expected_judgment:
            raise ValueError(f"Decision judgment contradicts evidence sufficiency for {intent_id}")

        if decision == "answer":
            if any(reviewed[field] == "N/A" for field in (
                "answer_correctness", "answer_completeness", "groundedness",
                "citation_support_overall", "output_language"
            )):
                raise ValueError(f"Answer row has N/A quality label: {intent_id}")
            language_compliant = reviewed["output_language"] in {
                "Vietnamese", "Mixed technical terms acceptable"
            }
            strict_answer = (
                evidence_sufficient
                and decision_correct
                and reviewed["answer_correctness"] == "Correct"
                and reviewed["answer_completeness"] == "Complete"
                and reviewed["groundedness"] == "Grounded"
                and reviewed["citation_support_overall"] == "All support"
                and language_compliant
            )
        else:
            if any(reviewed[field] != "N/A" for field in (
                "answer_correctness", "answer_completeness", "groundedness",
                "citation_support_overall", "output_language"
            )):
                raise ValueError(f"Abstain row must use N/A quality labels: {intent_id}")
            language_compliant = True
            strict_answer = False

        strict_e2e = strict_answer if evidence_sufficient else decision == "abstain"
        failures: list[str] = []
        if not decision_correct:
            failures.append("decision")
        if decision == "answer" and not strict_answer:
            failures.append("answer_quality_or_citation")
        if decision == "answer" and not language_compliant:
            failures.append("language")
        evaluated.append({
            **reviewed,
            "decision_correct": str(decision_correct).lower(),
            "language_compliant": str(language_compliant).lower(),
            "strict_answer_success": str(strict_answer).lower(),
            "strict_end_to_end_success": str(strict_e2e).lower(),
            "failure_reason": "|".join(failures),
        })
    return evaluated


def proportion(successes: int, total: int) -> dict[str, Any]:
    if total <= 0:
        raise ValueError("A reported M6 proportion must have a positive denominator")
    low, high = wilson_interval(successes, total)
    return {
        "numerator": successes,
        "denominator": total,
        "rate": successes / total,
        "wilson_95": [low, high],
    }


def compute_metrics_and_gates(
    prereg: dict[str, Any],
    evaluated: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = [row for row in evaluated if row["evaluation_scope"] == "primary"]
    if len(primary) != 19:
        raise ValueError("M6 requires exactly 19 primary reviewed records")
    answer_rows = [row for row in primary if row["decision"] == "answer"]
    if not answer_rows:
        raise ValueError("M6 language compliance has no answer-row denominator")

    decision_count = sum(row["decision_correct"] == "true" for row in primary)
    language_count = sum(row["language_compliant"] == "true" for row in answer_rows)
    strict_answer_count = sum(row["strict_answer_success"] == "true" for row in primary)
    strict_e2e_count = sum(row["strict_end_to_end_success"] == "true" for row in primary)
    metrics = {
        "schema_version": "multilingual_runtime_v1_m6_metrics_v1",
        "primary_count": len(primary),
        "excluded_intent_ids": sorted(PRIMARY_EXCLUDED_IDS),
        "decision_correct": proportion(decision_count, len(primary)),
        "language_compliance": proportion(language_count, len(answer_rows)),
        "strict_answer_success_diagnostic": proportion(strict_answer_count, len(primary)),
        "strict_end_to_end_success": proportion(strict_e2e_count, len(primary)),
        "matched_english_reference": prereg["frozen_english_matched_baseline"],
    }
    gate_conditions = {
        "G1_review_integrity": {
            "result": "PASS",
            "reviewed_count": len(evaluated),
            "primary_count": len(primary),
            "excluded_count": len(evaluated) - len(primary),
        },
        "G2_language_compliance": {
            "result": "PASS" if language_count == len(answer_rows) else "FAIL",
            "compliant_count": language_count,
            "answer_count": len(answer_rows),
        },
        "G3_decision_non_inferiority": {
            "result": "PASS" if decision_count >= DECISION_MINIMUM else "FAIL",
            "observed_count": decision_count,
            "minimum_required_count": DECISION_MINIMUM,
        },
        "G4_strict_end_to_end_non_inferiority": {
            "result": "PASS" if strict_e2e_count >= STRICT_E2E_MINIMUM else "FAIL",
            "observed_count": strict_e2e_count,
            "minimum_required_count": STRICT_E2E_MINIMUM,
        },
    }
    output_by_id = {str(row["intent_id"]): row for row in outputs}
    strict_failure_ids = [
        row["intent_id"] for row in primary
        if row["strict_end_to_end_success"] != "true"
    ]
    diagnostics = {
        "role": "post-review_observation_only_no_causal_attribution",
        "decision_failure_intent_ids": [
            row["intent_id"] for row in primary if row["decision_correct"] != "true"
        ],
        "strict_end_to_end_failure_intent_ids": strict_failure_ids,
        "normalization_applied_intent_ids": [
            row["intent_id"] for row in outputs if row["normalization_applied"]
        ],
        "strict_failure_runtime_context": [
            {
                "intent_id": intent_id,
                "retrieval_query": output_by_id[intent_id]["retrieval_query"],
                "top3_chunk_ids": output_by_id[intent_id]["top3_chunk_ids"],
                "normalization_applied": output_by_id[intent_id]["normalization_applied"],
                "normalization_reason": output_by_id[intent_id]["normalization_reason"],
            }
            for intent_id in strict_failure_ids
        ],
        "interpretation_boundary": (
            "These fields are joined only after primary labels are complete. They support "
            "diagnosis but do not establish translation-, retrieval-, or generation-level causality."
        ),
    }
    gates = {
        "all_passed": all(value["result"] == "PASS" for value in gate_conditions.values()),
        "conditions": gate_conditions,
        "pass_rule": "G1, G2, G3 and G4 must all PASS",
    }
    return {"metrics": metrics, "gates": gates, "diagnostics": diagnostics}


def evaluate(prereg: dict[str, Any]) -> None:
    if not WORKSHEET.exists() or not PREPARATION_MANIFEST.exists():
        raise FileNotFoundError("M6 must be prepared before evaluation")
    if not REVIEWED_WORKSHEET.exists():
        raise FileNotFoundError("M6 reviewed worksheet is missing")
    if any(path.exists() for path in (FINAL_RESULTS, METRICS, EVALUATION_MANIFEST)):
        raise FileExistsError("M6 evaluation outputs already exist")
    preparation = load_json(PREPARATION_MANIFEST)
    if preparation["worksheet"]["sha256"] != sha256_file(WORKSHEET):
        raise ValueError("Canonical M6 worksheet changed after preparation")
    if preparation["preregistration"]["sha256"] != sha256_file(PREREGISTRATION):
        raise ValueError("M6 pre-registration changed after worksheet preparation")

    canonical_header, canonical_rows = load_csv(WORKSHEET)
    reviewed_header, reviewed_rows = load_csv(REVIEWED_WORKSHEET)
    if canonical_header != WORKSHEET_FIELDS:
        raise ValueError("Canonical M6 worksheet header differs from the frozen schema")
    if reviewed_header != WORKSHEET_FIELDS:
        raise ValueError("Reviewed M6 worksheet header differs from the frozen schema")
    evaluated = validate_reviewed_rows(prereg, canonical_rows, reviewed_rows)
    result = compute_metrics_and_gates(prereg, evaluated, load_jsonl(M5_OUTPUTS))
    write_atomic(FINAL_RESULTS, serialize_csv(evaluated, WORKSHEET_FIELDS + DERIVED_FIELDS))
    write_json(METRICS, result)
    manifest = {
        "schema_version": "multilingual_runtime_v1_m6_evaluation_manifest_v1",
        "milestone": "multilingual_runtime_v1_m6",
        "status": "evaluated_passed" if result["gates"]["all_passed"] else "evaluated_failed",
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "preparation_manifest_sha256": sha256_file(PREPARATION_MANIFEST),
        "reviewed_worksheet_sha256": sha256_file(REVIEWED_WORKSHEET),
        "quality_metrics_computed": True,
        "runtime_calls": 0,
        "ground_truth_modified": False,
        "gates": result["gates"],
        "output_artifacts": [
            {
                "file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "sha256": sha256_file(path),
            }
            for path in (FINAL_RESULTS, METRICS)
        ],
    }
    write_json(EVALUATION_MANIFEST, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    prereg = verify_preregistration()
    rows = build_worksheet_rows(prereg)
    print(f"M6 protocol verified: {len(rows)} rows, no runtime call.")
    if args.verify_only:
        return
    if args.prepare:
        prepare(prereg)
        print(f"Prepared: {WORKSHEET.relative_to(PROJECT_ROOT)}")
        return
    evaluate(prereg)
    print(f"Evaluated: {EVALUATION_MANIFEST.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
