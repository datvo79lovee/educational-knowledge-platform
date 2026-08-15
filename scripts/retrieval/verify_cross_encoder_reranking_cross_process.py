"""So sánh artifact M2 với một lần reranking ở Python process độc lập."""

import csv
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = PROJECT_ROOT / "scripts/retrieval/evaluate_cross_encoder_reranking.py"
REPORT_ROOT = PROJECT_ROOT / "reports/11_reranking"
OUTPUT_NAMES = (
    "cross_encoder_reranking_results.csv",
    "cross_encoder_reranking_comparison.csv",
    "cross_encoder_reranking_question_comparison.csv",
    "cross_encoder_reranking_validation.csv",
    "cross_encoder_reranking_manifest.json",
)
REPORT = REPORT_ROOT / "cross_encoder_reranking_cross_process_validation.csv"


def sha256_file(path: Path) -> str:
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
    canonical = {name: sha256_file(REPORT_ROOT / name) for name in OUTPUT_NAMES}
    data_folder = PROJECT_ROOT / "data"
    data_folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reranking_cross_process_", dir=data_folder) as temp:
        verification_folder = Path(temp)
        subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                str(EVALUATOR),
                "--output-folder",
                str(verification_folder),
            ],
            cwd=PROJECT_ROOT,
            check=True,
        )
        verification = {
            name: sha256_file(verification_folder / name) for name in OUTPUT_NAMES
        }

    rows = [
        {
            "artifact": name,
            "canonical_sha256": canonical[name],
            "verification_process_sha256": verification[name],
            "hashes_match": canonical[name] == verification[name],
            "cross_process_deterministic": canonical[name] == verification[name],
        }
        for name in OUTPUT_NAMES
    ]
    if not all(row["hashes_match"] for row in rows):
        mismatches = [row["artifact"] for row in rows if not row["hashes_match"]]
        raise RuntimeError(f"Cross-Encoder outputs differ across processes: {mismatches}")

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    write_atomic(REPORT, buffer.getvalue().encode("utf-8-sig"))
    print("Cross-Encoder reranking cross-process deterministic: True")


if __name__ == "__main__":
    main()
