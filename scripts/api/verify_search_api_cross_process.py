"""Chạy Search API validator ở hai process và so byte với canonical reports."""

from __future__ import annotations

import csv
import hashlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = PROJECT_ROOT / "scripts/api/validate_search_api.py"
CANONICAL_DIR = PROJECT_ROOT / "reports/12_search_api"
OUTPUT_FILE = CANONICAL_DIR / "search_api_cross_process_validation.csv"
ARTIFACTS = (
    "search_api_answerable_validation.csv",
    "search_api_out_of_scope_validation.csv",
    "search_api_video_validation.csv",
    "search_api_failure_validation.csv",
    "search_api_citation_validation.csv",
    "search_api_validation_manifest.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mit60001_search_api_cross_process_") as raw_dir:
        root = Path(raw_dir)
        run_a = root / "run_a"
        run_b = root / "run_b"
        for output_dir in (run_a, run_b):
            subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(VALIDATOR),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=PROJECT_ROOT,
                check=True,
            )

        rows = []
        for artifact in ARTIFACTS:
            path_a = run_a / artifact
            path_b = run_b / artifact
            canonical = CANONICAL_DIR / artifact
            if not canonical.is_file():
                raise FileNotFoundError(f"Canonical validation artifact missing: {canonical}")
            hash_a = sha256_file(path_a)
            hash_b = sha256_file(path_b)
            canonical_hash = sha256_file(canonical)
            process_match = hash_a == hash_b
            canonical_match = hash_a == canonical_hash
            rows.append(
                {
                    "artifact": f"reports/12_search_api/{artifact}",
                    "run_a_sha256": hash_a,
                    "run_b_sha256": hash_b,
                    "canonical_sha256": canonical_hash,
                    "run_a_run_b_byte_identical": process_match,
                    "canonical_byte_identical": canonical_match,
                    "validation_status": (
                        "passed" if process_match and canonical_match else "failed"
                    ),
                }
            )

        if any(row["validation_status"] != "passed" for row in rows):
            raise ValueError("Search API validation is not deterministic across processes")
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        write_atomic(OUTPUT_FILE, buffer.getvalue().encode("utf-8-sig"))
        print(f"validated_artifacts={len(rows)}")
        print("cross_process_validation=passed")


if __name__ == "__main__":
    main()
