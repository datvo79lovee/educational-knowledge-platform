"""Xác minh Silver sample deterministic bằng hai Python process độc lập."""

import csv
import hashlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cleaning.silver_builder import write_bytes_atomically


SAMPLE_BUILDER = PROJECT_ROOT / "scripts/cleaning/build_silver_sample.py"
REPORT_FILE = Path("reports/07_cleaning/sample_cross_process_validation.csv")


def sha256_file(path: Path) -> str:
    """Tính SHA-256 file output để so sánh byte giữa hai process."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_builder(output_path: Path, report_path: Path) -> None:
    """Chạy sample wrapper ở một Python process mới với output tạm riêng."""

    subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SAMPLE_BUILDER),
            "--output",
            str(output_path),
            "--report",
            str(report_path),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def write_report(run_one_hash: str, run_two_hash: str, hashes_match: bool) -> None:
    """Ghi evidence cross-process không chứa transcript text."""

    fields = [
        "selection",
        "run_1_sha256",
        "run_2_sha256",
        "hashes_match",
        "cross_process_deterministic",
    ]
    row = {
        "selection": "fixed_five_video_sample",
        "run_1_sha256": run_one_hash,
        "run_2_sha256": run_two_hash,
        "hashes_match": hashes_match,
        "cross_process_deterministic": hashes_match,
    }
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerow(row)
    write_bytes_atomically(REPORT_FILE, buffer.getvalue().encode("utf-8-sig"))


def main() -> None:
    """Tạo hai output tạm bằng hai process, so sánh hash rồi hủy file tạm."""

    with tempfile.TemporaryDirectory(prefix="silver-sample-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        run_one_output = temporary_path / "run_one.jsonl"
        run_two_output = temporary_path / "run_two.jsonl"
        run_builder(run_one_output, temporary_path / "run_one_report.csv")
        run_builder(run_two_output, temporary_path / "run_two_report.csv")
        run_one_hash = sha256_file(run_one_output)
        run_two_hash = sha256_file(run_two_output)

    hashes_match = run_one_hash == run_two_hash
    write_report(run_one_hash, run_two_hash, hashes_match)
    print(f"Run 1 SHA-256               : {run_one_hash}")
    print(f"Run 2 SHA-256               : {run_two_hash}")
    print(f"Cross-process deterministic : {hashes_match}")

    if not hashes_match:
        raise RuntimeError("Two independent Python processes produced different bytes")


if __name__ == "__main__":
    main()
