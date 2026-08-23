"""Validate M3 metrics, controls, provenance, and deterministic evaluator reruns."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from evaluate_multilingual_retrieval_m3 import (
    DEFAULT_OUTPUT_DIR,
    MANIFEST_NAME,
    METRICS_NAME,
    M1_ARTIFACT,
    M1_MANIFEST,
    M2_MANIFEST,
    M2_RESULTS,
    README_NAME,
    RESULTS_NAME,
    build_artifacts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = PROJECT_ROOT / "scripts/evaluation/evaluate_multilingual_retrieval_m3.py"
EXPECTED_FILES = {RESULTS_NAME, METRICS_NAME, MANIFEST_NAME, README_NAME}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_fresh(output_dir: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    subprocess.run(
        [sys.executable, "-X", "utf8", str(EVALUATOR), "--output-dir", str(output_dir)],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    output_files = {path.name for path in DEFAULT_OUTPUT_DIR.iterdir() if path.is_file()}
    if output_files != EXPECTED_FILES:
        raise ValueError(f"M3 report folder must contain exactly four artifacts: {sorted(output_files)}")
    manifest = json.loads((DEFAULT_OUTPUT_DIR / MANIFEST_NAME).read_text(encoding="utf-8"))
    metrics = json.loads((DEFAULT_OUTPUT_DIR / METRICS_NAME).read_text(encoding="utf-8"))
    if manifest["validation_status"] != "passed" or manifest["status"] != "descriptive_baseline_complete":
        raise ValueError("M3 manifest is not complete/passed")
    source_paths = {
        "m1_paired_artifact": M1_ARTIFACT,
        "m1_manifest": M1_MANIFEST,
        "m2_results": M2_RESULTS,
        "m2_manifest": M2_MANIFEST,
    }
    for name, path in source_paths.items():
        if manifest["sources"][name]["sha256"] != sha256_file(path):
            raise ValueError(f"M3 source hash mismatch: {name}")
    artifact_paths = {
        "results": DEFAULT_OUTPUT_DIR / RESULTS_NAME,
        "metrics": DEFAULT_OUTPUT_DIR / METRICS_NAME,
        "readme": DEFAULT_OUTPUT_DIR / README_NAME,
    }
    for name, path in artifact_paths.items():
        if manifest["artifacts"][name]["sha256"] != sha256_file(path):
            raise ValueError(f"M3 artifact hash mismatch: {name}")

    with (DEFAULT_OUTPUT_DIR / RESULTS_NAME).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 20 or len({row["intent_id"] for row in rows}) != 20:
        raise ValueError("M3 per-intent results must contain 20 unique intents")
    q008 = next(row for row in rows if row["intent_id"] == "mit60001-q-008")
    if q008["translation_review_status"] != "Minor wording difference":
        raise ValueError("M3 q-008 trace missing")
    for control_id in ("mit60001-q-003", "mit60001-q-022"):
        row = next(item for item in rows if item["intent_id"] == control_id)
        pairs = [
            ("en_first_relevant_rank", "vi_first_relevant_rank"),
            ("en_recall_at_1", "vi_recall_at_1"),
            ("en_recall_at_3", "vi_recall_at_3"),
            ("en_recall_at_5", "vi_recall_at_5"),
            ("en_full_evidence_at_3", "vi_full_evidence_at_3"),
        ]
        if any(row[left] != row[right] for left, right in pairs):
            raise ValueError(f"M3 exact-string control failed: {control_id}")

    execution = manifest["execution"]
    if any(execution[field] != 0 for field in execution):
        raise ValueError("M3 execution contract contains forbidden calls/modifications")
    if metrics["quality_gate"]["defined"]:
        raise ValueError("M3 must not define a post-hoc quality gate")
    rebuilt = build_artifacts()
    for name, content in rebuilt.items():
        if sha256_bytes(content) != sha256_file(DEFAULT_OUTPUT_DIR / name):
            raise ValueError(f"M3 canonical artifact differs from evaluator rebuild: {name}")

    with tempfile.TemporaryDirectory(prefix="mit60001_m3_") as temporary:
        root = Path(temporary)
        run_a = root / "run_a"
        run_b = root / "run_b"
        run_fresh(run_a)
        run_fresh(run_b)
        for name in EXPECTED_FILES:
            hashes = {
                sha256_file(run_a / name),
                sha256_file(run_b / name),
                sha256_file(DEFAULT_OUTPUT_DIR / name),
            }
            if len(hashes) != 1:
                raise RuntimeError(f"M3 cross-process deterministic rerun failed: {name}")

    print(
        json.dumps(
            {
                "validation_status": "passed",
                "paired_intents_evaluated": 20,
                "headline_metrics": metrics["headline_metrics"],
                "paired_outcomes": metrics["paired_first_relevant_rank_outcomes"],
                "mean_top_3_overlap": metrics["top_3_overlap_diagnostic"]["mean_overlap_rate"],
                "exact_top_3_match_count": metrics["top_3_overlap_diagnostic"]["exact_top_3_match_count"],
                "exact_string_controls": "2/2 passed",
                "q_008_trace_preserved": True,
                "retrieval_reruns": 0,
                "translator_calls": 0,
                "ground_truth_modifications": 0,
                "deterministic_evaluator_rerun": "passed",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
