"""Xác minh hai process tạo retrieval comparison byte-identical."""

import csv
import hashlib
import io
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = PROJECT_ROOT / "scripts" / "chunking" / "evaluate_chunk_retrieval.py"
REPORT_ROOT = PROJECT_ROOT / "reports" / "08_chunking"
OUTPUTS = (
    REPORT_ROOT / "chunking_retrieval_results.csv",
    REPORT_ROOT / "chunking_comparison.csv",
    REPORT_ROOT / "retrieval_run_manifest.json",
)
REPORT = REPORT_ROOT / "retrieval_cross_process_validation.csv"


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    command = [sys.executable, "-X", "utf8", str(EVALUATOR)]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    first = {path.name: hash_file(path) for path in OUTPUTS}
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    second = {path.name: hash_file(path) for path in OUTPUTS}
    rows = [
        {
            "artifact": path.name,
            "run_1_sha256": first[path.name],
            "run_2_sha256": second[path.name],
            "hashes_match": first[path.name] == second[path.name],
            "cross_process_deterministic": first[path.name] == second[path.name],
        }
        for path in OUTPUTS
    ]
    if not all(row["hashes_match"] for row in rows):
        raise RuntimeError("Retrieval output differs across Python processes")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Retrieval cross-process deterministic: True")


if __name__ == "__main__":
    main()
