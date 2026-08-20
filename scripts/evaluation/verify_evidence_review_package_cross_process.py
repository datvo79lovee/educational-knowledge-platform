"""Rebuild M2A package in two Python processes and compare canonical bytes."""

from __future__ import annotations

import csv
import hashlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "scripts/evaluation/build_evidence_review_package.py"
REPORT = PROJECT_ROOT / "reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_cross_process_validation.csv"
ARTIFACTS = (
    Path("evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl"),
    Path("evaluation/review/evidence_accept_reject/evidence_review_calibration_v1.csv"),
    Path("reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_validation.csv"),
    Path("reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_manifest.json"),
)


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def run_builder(output_root: Path) -> None:
    subprocess.run(
        [sys.executable, "-X", "utf8", str(BUILDER), "--output-root", str(output_root)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def serialize_csv(rows: list[dict[str, object]]) -> bytes:
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


def main() -> None:
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mit60001_evidence_review_run1_") as run1_raw:
        with tempfile.TemporaryDirectory(prefix="mit60001_evidence_review_run2_") as run2_raw:
            run1_root = Path(run1_raw)
            run2_root = Path(run2_raw)
            run_builder(run1_root)
            run_builder(run2_root)
            for artifact in ARTIFACTS:
                canonical_sha256 = sha256_file(PROJECT_ROOT / artifact)
                run1_sha256 = sha256_file(run1_root / artifact)
                run2_sha256 = sha256_file(run2_root / artifact)
                rows.append(
                    {
                        "artifact": artifact.as_posix(),
                        "canonical_sha256": canonical_sha256,
                        "process_1_sha256": run1_sha256,
                        "process_2_sha256": run2_sha256,
                        "canonical_match": canonical_sha256 == run1_sha256 == run2_sha256,
                        "cross_process_match": run1_sha256 == run2_sha256,
                        "validation_status": (
                            "passed" if canonical_sha256 == run1_sha256 == run2_sha256 else "failed"
                        ),
                    }
                )
    if not all(row["validation_status"] == "passed" for row in rows):
        raise ValueError("Evidence-review package is not byte-identical across processes")
    write_atomic(REPORT, serialize_csv(rows))
    print(f"validated_artifacts={len(rows)} status=passed")


if __name__ == "__main__":
    main()
