"""Verify M2 results and manifest are byte-identical across fresh Python processes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_SCRIPT = PROJECT_ROOT / "scripts/evaluation/run_multilingual_dense_retrieval_m2.py"
REPORT_DIR = PROJECT_ROOT / "reports/27_multilingual_dense_retrieval"
RESULTS_NAME = "multilingual_dense_retrieval_results.jsonl"
MANIFEST_NAME = "multilingual_dense_retrieval_manifest.json"
OUTPUT_FILE = REPORT_DIR / "multilingual_dense_retrieval_cross_process_validation.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_once(output_dir: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    subprocess.run(
        [sys.executable, "-X", "utf8", str(RUN_SCRIPT), "--output-dir", str(output_dir)],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mit60001_m2_") as temporary:
        root = Path(temporary)
        run_a = root / "run_a"
        run_b = root / "run_b"
        run_once(run_a)
        run_once(run_b)
        results_a = sha256_file(run_a / RESULTS_NAME)
        results_b = sha256_file(run_b / RESULTS_NAME)
        manifest_a = sha256_file(run_a / MANIFEST_NAME)
        manifest_b = sha256_file(run_b / MANIFEST_NAME)

    canonical_results = sha256_file(REPORT_DIR / RESULTS_NAME)
    canonical_manifest = sha256_file(REPORT_DIR / MANIFEST_NAME)
    passed = (
        results_a == results_b == canonical_results
        and manifest_a == manifest_b == canonical_manifest
    )
    report = {
        "schema_version": "multilingual_retrieval_cross_process_validation_v1",
        "results_run_a_sha256": results_a,
        "results_run_b_sha256": results_b,
        "canonical_results_sha256": canonical_results,
        "manifest_run_a_sha256": manifest_a,
        "manifest_run_b_sha256": manifest_b,
        "canonical_manifest_sha256": canonical_manifest,
        "results_byte_identical": results_a == results_b == canonical_results,
        "manifest_byte_identical": manifest_a == manifest_b == canonical_manifest,
        "validation_status": "passed" if passed else "failed",
    }
    if not passed:
        raise RuntimeError("M2 cross-process deterministic validation failed")
    write_atomic(OUTPUT_FILE, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
