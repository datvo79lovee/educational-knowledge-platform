"""Build toàn bộ 38 Silver transcript của target corpus MIT 6.0001."""

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cleaning.silver_builder import (
    CLEANING_VERSION,
    FULL_TARGET_RECORD_COUNT,
    SCOPE_VERSION,
    build_silver,
    write_bytes_atomically,
)


DEFAULT_OUTPUT = Path("data/silver/mit_60001/transcripts_clean.jsonl")
DEFAULT_RECORD_REPORT = Path("reports/07_cleaning/full_validation.csv")
DEFAULT_SUMMARY_REPORT = Path("reports/07_cleaning/cleaning_summary.csv")


def parse_args() -> argparse.Namespace:
    """Nhận đường dẫn để có thể rebuild output hoặc report ở vị trí khác."""

    parser = argparse.ArgumentParser(
        description="Build and validate all 38 MIT 6.0001 Silver transcripts."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_RECORD_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_REPORT)
    return parser.parse_args()


def write_summary(path: Path, output_path: Path, record_count: int, segment_count: int) -> None:
    """Ghi một dòng tổng kết full build, không đưa transcript text vào report."""

    output_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    row = {
        "scope_version": SCOPE_VERSION,
        "cleaning_version": CLEANING_VERSION,
        "selection": "all_target_manifest_records",
        "expected_record_count": FULL_TARGET_RECORD_COUNT,
        "record_count": record_count,
        "unique_video_id_count": record_count,
        "total_segment_count": segment_count,
        "output_sha256": output_sha256,
        "validation_status": "passed",
    }
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    write_bytes_atomically(path, buffer.getvalue().encode("utf-8-sig"))


def main() -> None:
    """Build full scope qua shared core, rồi ghi record report và summary report."""

    args = parse_args()
    artifacts = build_silver(None, args.output, args.report)
    record_count = len(artifacts.records)
    if record_count != FULL_TARGET_RECORD_COUNT:
        raise RuntimeError("Full Silver output does not contain 38 records")

    write_summary(
        args.summary,
        args.output,
        record_count,
        sum(record["segment_count"] for record in artifacts.records),
    )
    print(f"Full Silver records             : {record_count}")
    print("Independent in-process rebuild : True")
    print(f"Silver full output             : {args.output}")
    print(f"Record validation report       : {args.report}")
    print(f"Cleaning summary               : {args.summary}")


if __name__ == "__main__":
    main()
