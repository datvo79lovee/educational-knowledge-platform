"""Create read-only corpus audit reports from PostgreSQL and checkpoint JSONL."""

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


REPORTS_DIR = Path("reports")
CHECKPOINT_FILE = Path("data/bronze/transcripts_checkpoint.jsonl")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_checkpoint_summary() -> tuple[int, int, Counter, Counter]:
    statuses = Counter()
    latest_status_by_video = {}
    line_count = 0

    with CHECKPOINT_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Checkpoint JSON không hợp lệ tại dòng {line_number}: {error}"
                ) from error

            statuses[record.get("status", "missing_status")] += 1
            if record.get("video_id"):
                latest_status_by_video[record["video_id"]] = record.get(
                    "status", "missing_status"
                )

    latest_statuses = Counter(latest_status_by_video.values())
    return line_count, len(latest_status_by_video), statuses, latest_statuses


def fetch_database_data() -> tuple[list[tuple], list[tuple], list[tuple]]:
    connection = get_connection()

    try:
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COALESCE(EXTRACT(YEAR FROM v.publish_date)::INT::TEXT, 'unknown'),
                    COUNT(*),
                    COUNT(v.duration_seconds),
                    MIN(v.duration_seconds),
                    MAX(v.duration_seconds),
                    AVG(v.duration_seconds)
                FROM videos v
                GROUP BY 1
                ORDER BY 1
                """
            )
            yearly_video_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    s.source_id,
                    s.source_name,
                    COUNT(v.video_id),
                    MIN(v.publish_date),
                    MAX(v.publish_date),
                    COUNT(v.duration_seconds),
                    AVG(v.duration_seconds)
                FROM sources s
                LEFT JOIN videos v ON v.source_id = s.source_id
                GROUP BY s.source_id, s.source_name
                ORDER BY s.source_id
                """
            )
            source_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    v.video_id,
                    v.title,
                    v.description,
                    v.publish_date,
                    v.duration_seconds,
                    t.language,
                    LENGTH(t.raw_text) AS transcript_length,
                    t.retrieved_at
                FROM transcripts t
                JOIN videos v ON v.video_id = t.video_id
                ORDER BY v.video_id
                """
            )
            transcript_rows = cursor.fetchall()

        connection.rollback()
        return yearly_video_rows, source_rows, transcript_rows
    finally:
        connection.close()


def main() -> None:
    yearly_rows, source_rows, transcript_rows = fetch_database_data()
    (
        checkpoint_lines,
        checkpoint_videos,
        checkpoint_statuses,
        latest_checkpoint_statuses,
    ) = read_checkpoint_summary()

    video_summary = []
    for year, count, duration_count, min_duration, max_duration, avg_duration in yearly_rows:
        video_summary.append(
            {
                "summary_type": "publish_year",
                "group": year,
                "video_count": count,
                "duration_available_count": duration_count,
                "min_duration_seconds": min_duration,
                "max_duration_seconds": max_duration,
                "avg_duration_seconds": (
                    round(float(avg_duration), 2) if avg_duration is not None else ""
                ),
            }
        )

    for source_id, source_name, count, min_date, max_date, duration_count, avg_duration in source_rows:
        video_summary.append(
            {
                "summary_type": "source",
                "group": f"{source_id}:{source_name}",
                "video_count": count,
                "duration_available_count": duration_count,
                "min_duration_seconds": "",
                "max_duration_seconds": "",
                "avg_duration_seconds": (
                    round(float(avg_duration), 2) if avg_duration is not None else ""
                ),
            }
        )

    transcript_summary = [
        {
            "video_id": row[0],
            "title": row[1],
            "description": row[2],
            "publish_date": row[3],
            "duration_seconds": row[4],
            "language": row[5],
            "transcript_length": row[6],
            "retrieved_at": row[7],
        }
        for row in transcript_rows
    ]

    checkpoint_summary = [
        {
            "status": status,
            "historical_record_count": checkpoint_statuses.get(status, 0),
            "latest_video_count": latest_checkpoint_statuses.get(status, 0),
        }
        for status in sorted(set(checkpoint_statuses) | set(latest_checkpoint_statuses))
    ]

    write_csv(
        REPORTS_DIR / "video_summary.csv",
        [
            "summary_type",
            "group",
            "video_count",
            "duration_available_count",
            "min_duration_seconds",
            "max_duration_seconds",
            "avg_duration_seconds",
        ],
        video_summary,
    )
    write_csv(
        REPORTS_DIR / "transcript_summary.csv",
        [
            "video_id",
            "title",
            "description",
            "publish_date",
            "duration_seconds",
            "language",
            "transcript_length",
            "retrieved_at",
        ],
        transcript_summary,
    )
    write_csv(
        REPORTS_DIR / "checkpoint_status_summary.csv",
        ["status", "historical_record_count", "latest_video_count"],
        checkpoint_summary,
    )

    lengths = [row[6] for row in transcript_rows]
    duration_missing = sum(row[4] is None for row in transcript_rows)
    description_missing = sum(not row[2] for row in transcript_rows)

    print(f"Videos                    : {sum(row[1] for row in yearly_rows)}")
    print(f"Publish year groups        : {len(yearly_rows)}")
    print(f"Sources                    : {len(source_rows)}")
    print(f"Transcripts                : {len(transcript_rows)}")
    print(f"Missing descriptions       : {description_missing}")
    print(f"Missing transcript duration: {duration_missing}")
    print(f"Transcript length median   : {statistics.median(lengths):.1f}")
    print(f"Checkpoint lines           : {checkpoint_lines}")
    print(f"Checkpoint unique videos   : {checkpoint_videos}")
    for status, count in sorted(checkpoint_statuses.items()):
        latest_count = latest_checkpoint_statuses.get(status, 0)
        print(f"Checkpoint {status:<20}: history={count}, latest={latest_count}")


if __name__ == "__main__":
    main()
