"""Validate Bronze transcript JSONL and load it into PostgreSQL.

The loader is idempotent at the video level: a video that already has a row in
``transcripts`` is skipped. Use ``--commit`` to persist inserts; without it the
transaction is rolled back after validation.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from psycopg2.extras import execute_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


DEFAULT_INPUT = Path("data/bronze/transcripts_raw.jsonl")


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_raw_text(segments: list[dict]) -> str:
    texts = [segment.get("text", "").strip() for segment in segments]
    texts = [text for text in texts if text]
    return "\n".join(texts)


def read_records(input_path: Path) -> list[tuple[str, str, str, datetime]]:
    records = []
    seen_video_ids = set()

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number}: {error}") from error

            video_id = payload.get("video_id")
            language_code = payload.get("language_code")
            segments = payload.get("segments")
            fetched_at = payload.get("fetched_at")

            if not video_id:
                raise ValueError(f"Missing video_id at line {line_number}")
            if video_id in seen_video_ids:
                raise ValueError(f"Duplicate video_id at line {line_number}: {video_id}")
            if not language_code or len(language_code) > 20:
                raise ValueError(f"Invalid language_code at line {line_number}")
            if not isinstance(segments, list) or not segments:
                raise ValueError(f"Missing segments at line {line_number}")
            if not fetched_at:
                raise ValueError(f"Missing fetched_at at line {line_number}")

            raw_text = build_raw_text(segments)
            if not raw_text:
                raise ValueError(f"Empty transcript text at line {line_number}")

            records.append(
                (video_id, language_code, raw_text, parse_timestamp(fetched_at))
            )
            seen_video_ids.add(video_id)

    return records


def load_records(records: list[tuple], commit: bool) -> dict[str, int]:
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM transcripts")
            before_count = cursor.fetchone()[0]

            video_ids = [record[0] for record in records]
            cursor.execute(
                "SELECT video_id FROM videos WHERE video_id = ANY(%s)",
                (video_ids,),
            )
            database_video_ids = {row[0] for row in cursor.fetchall()}
            missing_video_ids = set(video_ids) - database_video_ids
            if missing_video_ids:
                sample = ", ".join(sorted(missing_video_ids)[:10])
                raise ValueError(
                    f"{len(missing_video_ids)} video_id(s) missing from videos: {sample}"
                )

            cursor.execute(
                "SELECT DISTINCT video_id FROM transcripts WHERE video_id = ANY(%s)",
                (video_ids,),
            )
            existing_video_ids = {row[0] for row in cursor.fetchall()}
            pending_records = [
                record for record in records if record[0] not in existing_video_ids
            ]

            if pending_records:
                execute_values(
                    cursor,
                    """
                    INSERT INTO transcripts
                        (video_id, language, raw_text, retrieved_at)
                    VALUES %s
                    """,
                    pending_records,
                    page_size=100,
                )

            cursor.execute("SELECT COUNT(*) FROM transcripts")
            after_count = cursor.fetchone()[0]
            expected_after = before_count + len(pending_records)
            if after_count != expected_after:
                raise RuntimeError(
                    f"Count verification failed: expected {expected_after}, got {after_count}"
                )

        if commit:
            connection.commit()
        else:
            connection.rollback()

        return {
            "input_records": len(records),
            "existing_records": len(existing_video_ids),
            "inserted_records": len(pending_records),
            "before_count": before_count,
            "after_count": after_count,
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and load Bronze transcripts into PostgreSQL."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist inserts. The default behavior validates and rolls back.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = read_records(args.input)
    result = load_records(records, commit=args.commit)

    print(f"Mode             : {'COMMIT' if args.commit else 'DRY RUN'}")
    print(f"Input records    : {result['input_records']}")
    print(f"Already existing : {result['existing_records']}")
    print(f"Inserted         : {result['inserted_records']}")
    print(f"Before count     : {result['before_count']}")
    print(f"After count      : {result['after_count']}")

    if not args.commit:
        print("No database changes were persisted.")


if __name__ == "__main__":
    main()
