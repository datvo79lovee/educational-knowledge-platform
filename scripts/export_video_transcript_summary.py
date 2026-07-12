"""Export the PostgreSQL video/transcript audit report as CSV.

This script is read-only. It does not load or modify database records.
"""

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


QUERY = """
    SELECT
        v.video_id,
        v.title,
        v.description,
        v.publish_date,
        t.language,
        LENGTH(t.raw_text) AS transcript_length
    FROM transcripts t
    JOIN videos v
        ON t.video_id = v.video_id
    ORDER BY v.video_id
"""

COUNT_QUERY = """
    SELECT
        (SELECT COUNT(*) FROM sources) AS sources,
        (SELECT COUNT(*) FROM videos) AS videos,
        (SELECT COUNT(*) FROM transcripts) AS transcripts
"""

FIELDNAMES = [
    "video_id",
    "title",
    "description",
    "publish_date",
    "language",
    "transcript_length",
]


def export_report(output_path: Path) -> tuple[int, int, int, int]:
    """Run the audit queries and write the joined records to ``output_path``."""

    connection = get_connection()

    try:
        connection.set_session(readonly=True, autocommit=False)

        with connection.cursor() as cursor:
            cursor.execute(COUNT_QUERY)
            source_count, video_count, transcript_count = cursor.fetchone()

            cursor.execute(QUERY)
            rows = cursor.fetchall()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(FIELDNAMES)
            writer.writerows(rows)

        connection.rollback()

        return source_count, video_count, transcript_count, len(rows)

    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a read-only PostgreSQL video/transcript audit report."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/video_transcript_summary.csv"),
        help="Destination CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources, videos, transcripts, exported = export_report(args.output)

    print(f"Sources in PostgreSQL     : {sources}")
    print(f"Videos in PostgreSQL      : {videos}")
    print(f"Transcripts in PostgreSQL : {transcripts}")
    print(f"Joined rows exported      : {exported}")
    print(f"Output                    : {args.output}")

    if transcripts == 0:
        print(
            "WARNING: The transcripts table is empty. "
            "Bronze transcript JSONL has not been loaded into PostgreSQL."
        )


if __name__ == "__main__":
    main()
