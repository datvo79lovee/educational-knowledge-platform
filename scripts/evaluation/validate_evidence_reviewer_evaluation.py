"""Validate canonical M3 human review, final metrics and artifact hashes."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluation.phase8_report_paths import resolve_manifest_path
MANIFEST_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_manifest.json"
MANIFEST_SCHEMA_FILE = PROJECT_ROOT / "schemas/evidence_reviewer_evaluation_final_manifest_v1.schema.json"
FINAL_RESULTS_FILE = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/final_decision_results.csv"
CANONICAL_HUMAN_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/m3_human_review_12_canonical.csv"
CANONICAL_EVIDENCE_FILE = PROJECT_ROOT / "evaluation/review/evidence_accept_reject/m3_evidence_entailment_canonical.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        raise ValueError(f"Final M3 manifest schema failed: {errors[0].message}")

    for artifact in manifest["output_artifacts"]:
        path = resolve_manifest_path(PROJECT_ROOT, artifact["file"])
        if not path.exists() or sha256_file(path) != artifact["sha256"]:
            raise ValueError(f"Final M3 artifact missing or hash mismatch: {artifact['file']}")

    reviewed_workbook = PROJECT_ROOT / manifest["reviewed_workbook"]["file"]
    if not reviewed_workbook.exists():
        raise ValueError("Reviewed workbook is missing")

    final_rows = load_csv(FINAL_RESULTS_FILE)
    human_rows = load_csv(CANONICAL_HUMAN_FILE)
    evidence_rows = load_csv(CANONICAL_EVIDENCE_FILE)
    if (len(final_rows), len(human_rows), len(evidence_rows)) != (40, 12, 35):
        raise ValueError("Expected 40 final, 12 human and 35 evidence rows")
    workbook_hashes = {row["source_workbook_sha256"] for row in human_rows + evidence_rows}
    if workbook_hashes != {manifest["reviewed_workbook"]["sha256"]}:
        raise ValueError("Canonical rows do not share the reviewed workbook SHA-256")
    if any(row["human_review_status"] != "reviewed" for row in human_rows + evidence_rows):
        raise ValueError("Canonical human review is not complete")

    evaluated = [row for row in final_rows if row["evaluation_status"] == "evaluated"]
    excluded = [row for row in final_rows if row["evaluation_status"] == "excluded"]
    if len(evaluated) != 37 or {row["question_id"] for row in excluded} != {
        "mit60001-q-017", "mit60001-q-023", "mit60001-q-041"
    }:
        raise ValueError("Final evaluated/excluded split is invalid")
    confusion = Counter((row["expected_decision"], row["predicted_decision"]) for row in evaluated)
    final_confusion = {
        "tp": confusion[("accept", "accept")],
        "fp": confusion[("reject", "accept")],
        "fn": confusion[("accept", "reject")],
        "tn": confusion[("reject", "reject")],
    }
    if final_confusion != manifest["final_metrics"]["confusion_matrix"]:
        raise ValueError("Final confusion matrix mismatch")
    verdicts = Counter(row["human_entailment_verdict"] for row in evidence_rows)
    if verdicts != {"supports": 27, "does_not_support": 8}:
        raise ValueError(f"Evidence verdict counts mismatch: {dict(verdicts)}")
    if manifest["ground_truth_modified"] or manifest["prompt_or_model_modified"]:
        raise ValueError("M3 must not modify Ground Truth, prompt or model")

    print(json.dumps({
        "evaluated_question_count": len(evaluated),
        "excluded_question_count": len(excluded),
        "confusion_matrix": final_confusion,
        "supporting_chunk_count": verdicts["supports"],
        "non_supporting_chunk_count": verdicts["does_not_support"],
        "validation_status": "passed",
        "m3_status": manifest["m3_status"],
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
