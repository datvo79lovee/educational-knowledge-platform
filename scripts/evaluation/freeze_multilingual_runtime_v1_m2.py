"""Freeze Multilingual Runtime V1 - M2 after human adjudication.

This script only records results that already exist. It reads the reviewed
adjudication worksheet, canonicalises the tally, closes gate G1, and writes the final
metrics and manifest. It never re-runs the translator, never touches the
pre-registration, the gates, the Ground Truth, the retriever or any frozen artifact.

The reviewed worksheet is hashed byte for byte, BOM included, exactly as the reviewer
saved it.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports/30_multilingual_runtime_v1_m2"
PREREGISTRATION = REPORT_DIR / "m2_preregistration.json"
REVIEWED_WORKSHEET = REPORT_DIR / "m2_adjudication_worksheet_reviewed.csv"
METRICS_FILE = REPORT_DIR / "m2_metrics.json"
MANIFEST_FILE = REPORT_DIR / "m2_manifest.json"

RUBRIC = ("Equivalent", "Minor wording difference", "Semantic drift")
DRIFT_LABEL = "Semantic drift"
EXPECTED_INTENT_COUNT = 20


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_file_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_reviewed_rows() -> list[dict[str, str]]:
    """Decode with utf-8-sig for parsing only; the file itself is never rewritten."""

    text = REVIEWED_WORKSHEET.read_bytes().decode("utf-8-sig")
    rows = [row for row in csv.DictReader(io.StringIO(text)) if row.get("intent_id")]
    if len(rows) != EXPECTED_INTENT_COUNT:
        raise ValueError(f"Reviewed worksheet must hold {EXPECTED_INTENT_COUNT} rows, found {len(rows)}")
    unlabelled = [row["intent_id"] for row in rows if row["adjudication"] not in RUBRIC]
    if unlabelled:
        raise ValueError("Rows outside the M1 rubric: " + ", ".join(unlabelled))
    return rows


def verify_review_matches_execution(rows: list[dict[str, str]], metrics: dict[str, Any]) -> None:
    """The review must describe the executed outputs, not a stale worksheet copy."""

    executed = {row["intent_id"]: row["machine_literal_en"] for row in metrics["per_intent"]}
    reviewed = {row["intent_id"]: row["machine_literal_en"] for row in rows}
    if set(executed) != set(reviewed):
        raise ValueError("Reviewed worksheet intent set differs from the executed run")
    drifted = [intent_id for intent_id, value in reviewed.items() if executed[intent_id] != value]
    if drifted:
        raise ValueError("Reviewed worksheet text differs from executed output: " + ", ".join(sorted(drifted)))


def main() -> None:
    prereg = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))

    if metrics["preregistration_sha256"] != sha256_file(PREREGISTRATION):
        raise ValueError("Pre-registration changed after execution")

    rows = read_reviewed_rows()
    verify_review_matches_execution(rows, metrics)

    tally = {label: sum(1 for row in rows if row["adjudication"] == label) for label in RUBRIC}
    drift_intent_ids = sorted(row["intent_id"] for row in rows if row["adjudication"] == DRIFT_LABEL)
    gate_g1 = next(item for item in prereg["primary_gate"]["conditions_all_must_hold"] if item["id"] == "G1")
    g1_threshold = gate_g1["threshold"]
    g1_pass = tally[DRIFT_LABEL] <= g1_threshold

    g2_pass = metrics["gate_G2_recall_at_3"]["result"] == "PASS"
    determinism_pass = bool(metrics["determinism"]["all_runs_identical"])
    overall_pass = g1_pass and g2_pass

    worksheet_hash = sha256_file(REVIEWED_WORKSHEET)

    human_adjudication = {
        "worksheet": str(REVIEWED_WORKSHEET.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "worksheet_sha256_raw_bytes": worksheet_hash,
        "byte_note": "Hashed exactly as saved by the reviewer, UTF-8 BOM included; the file is never rewritten.",
        "rubric": list(RUBRIC),
        "tally": tally,
        "semantic_drift_intent_ids": drift_intent_ids,
        "reviewed_row_count": len(rows),
    }

    metrics["status"] = "final_failed"
    metrics["human_adjudication"] = human_adjudication
    metrics["gate_G1_semantic_drift"] = {
        "threshold": g1_threshold,
        "observed_semantic_drift": tally[DRIFT_LABEL],
        "result": "PASS" if g1_pass else "FAIL",
        "worksheet": human_adjudication["worksheet"],
        "worksheet_sha256_raw_bytes": worksheet_hash,
    }
    metrics["determinism_gate"] = {
        "expectation": "run A and run B translations byte-identical for all 20 intents",
        "result": "PASS" if determinism_pass else "FAIL",
        "mismatched_intent_ids": metrics["determinism"]["compared_pairs"][0]["mismatched_intent_ids"],
        "scope_note": (
            "This measures the literal translator only. It shows that the repository's earlier "
            "deterministic-rerun guarantees cannot be assumed to extend to Ollama generation in "
            "general. It is not evidence about the G0 English generator, which would need its own test."
        ),
    }
    metrics["overall_result"] = {
        "result": "FAIL",
        "rule": "primary gate is the conjunction of G1 and G2",
        "vi_runtime_candidate": "REJECTED",
        "failed_conditions": [name for name, ok in (("G1", g1_pass), ("G2", g2_pass)) if not ok],
    }
    write_json(METRICS_FILE, metrics)

    manifest["status"] = "frozen_failed"
    manifest["gate_results"] = {
        "G1": "PASS" if g1_pass else "FAIL",
        "G2": metrics["gate_G2_recall_at_3"]["result"],
        "determinism": "PASS" if determinism_pass else "FAIL",
        "P1": metrics["prediction_P1"]["result"],
        "overall": "PASS" if overall_pass else "FAIL",
        "vi_runtime_candidate": "REJECTED" if not overall_pass else "ACCEPTED",
    }
    manifest["human_adjudication"] = human_adjudication
    manifest["analysis_code_sha256_lf_normalized"][
        "scripts/evaluation/freeze_multilingual_runtime_v1_m2.py"
    ] = sha256_file_lf(Path(__file__))
    manifest["output_artifacts"] = [
        {"file": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"), "sha256": sha256_file(path)}
        for path in (
            REPORT_DIR / "m2_machine_translations.jsonl",
            REPORT_DIR / "m2_machine_retrieval_results.jsonl",
            REPORT_DIR / "m2_adjudication_worksheet.csv",
            REVIEWED_WORKSHEET,
            METRICS_FILE,
        )
    ]
    manifest["validation_status"] = "passed"
    write_json(MANIFEST_FILE, manifest)

    print(json.dumps(
        {
            "status": manifest["status"],
            "tally": tally,
            "gate_results": manifest["gate_results"],
            "worksheet_sha256_raw_bytes": worksheet_hash,
            "semantic_drift_intent_ids": drift_intent_ids,
        },
        indent=2, ensure_ascii=False, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
