"""Build đúng năm Silver sample bằng shared Silver build core."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cleaning.silver_builder import build_silver


SAMPLE_VIDEO_IDS = {
    "nykOeWgQcHM",
    "w4uxYDPsjbw",
    "FlGjISF3l78",
    "o9nW0uBqvEo",
    "6LOwPhPDwVc",
}

DEFAULT_OUTPUT = Path(
    "data/silver/mit_60001/samples/transcripts_clean_sample.jsonl"
)
DEFAULT_REPORT = Path("reports/07_cleaning/sample_validation.csv")


def parse_args() -> argparse.Namespace:
    """Nhận đường dẫn output/report để cross-process verifier dùng output tạm."""

    parser = argparse.ArgumentParser(
        description="Build and validate the fixed five-video Silver sample."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    """Gọi shared core với năm sample ID, không có đường chạy full corpus ở đây."""

    args = parse_args()
    artifacts = build_silver(SAMPLE_VIDEO_IDS, args.output, args.report)
    print(f"Sample records                 : {len(artifacts.records)}")
    print("Independent in-process rebuild : True")
    print(f"Silver sample output           : {args.output}")
    print(f"Validation report              : {args.report}")


if __name__ == "__main__":
    main()
