"""Kiểm tra transcript của target corpus sau khi load vào PostgreSQL.

Script đọc manifest MIT 6.0001, JOIN bảng ``videos`` và ``transcripts``, sau đó
kiểm tra coverage, dữ liệu rỗng và video bị lặp. Kết quả được xuất thành CSV nhưng
không chứa ``raw_text``. Kết nối PostgreSQL luôn ở chế độ read-only.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


SCOPE_VERSION = "mit_60001_fall_2016_v1"
EXPECTED_TARGET_VIDEOS = 38
EXPECTED_TOTAL_TRANSCRIPTS = 324

MANIFEST_FILE = Path("reports/04_scope_decision/target_manifest.csv")
REPORTS_DIR = Path("reports/06_transcript_load_validation")
SUMMARY_FILE = REPORTS_DIR / "validation_summary.csv"
DETAIL_FILE = REPORTS_DIR / "target_transcript_validation.csv"


def load_manifest() -> list[dict]:
    """Đọc và kiểm tra manifest điều khiển phạm vi validation."""

    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Target manifest does not exist: {MANIFEST_FILE}")

    with MANIFEST_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if len(rows) != EXPECTED_TARGET_VIDEOS:
        raise ValueError(
            f"Expected {EXPECTED_TARGET_VIDEOS} manifest rows, found {len(rows)}"
        )

    video_ids = [row["video_id"] for row in rows]
    duplicates = [
        video_id
        for video_id, count in Counter(video_ids).items()
        if count > 1
    ]
    if duplicates:
        raise ValueError(f"Duplicate video IDs in manifest: {duplicates}")

    for row in rows:
        if row["scope_version"] != SCOPE_VERSION:
            raise ValueError(
                f"Unexpected scope version for {row['video_id']}: "
                f"{row['scope_version']}"
            )

    return sorted(rows, key=lambda row: int(row["playlist_position"]))


def fetch_validation_state(
    manifest: list[dict],
) -> tuple[int, list[dict], list[str], list[str]]:
    """Đọc tổng count và JOIN target từ PostgreSQL trong một transaction read-only.

    Giá trị trả về gồm tổng transcript toàn database, các dòng JOIN, video thiếu
    metadata và video thiếu transcript.
    """

    target_ids = [row["video_id"] for row in manifest]
    connection = get_connection()

    try:
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM transcripts")
            total_transcripts = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    v.video_id,
                    v.title,
                    v.publish_date,
                    t.language,
                    LENGTH(t.raw_text) AS transcript_length,
                    t.retrieved_at
                FROM videos AS v
                JOIN transcripts AS t
                    ON t.video_id = v.video_id
                WHERE v.video_id = ANY(%s)
                """,
                (target_ids,),
            )
            joined_rows = [
                {
                    "video_id": row[0],
                    "postgres_title": row[1],
                    "publish_date": row[2],
                    "language": row[3],
                    "transcript_length": row[4],
                    "retrieved_at": row[5],
                }
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT target.video_id
                FROM unnest(%s::text[]) AS target(video_id)
                LEFT JOIN videos AS v
                    ON v.video_id = target.video_id
                WHERE v.video_id IS NULL
                ORDER BY target.video_id
                """,
                (target_ids,),
            )
            missing_video_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                """
                SELECT target.video_id
                FROM unnest(%s::text[]) AS target(video_id)
                LEFT JOIN transcripts AS t
                    ON t.video_id = target.video_id
                WHERE t.video_id IS NULL
                ORDER BY target.video_id
                """,
                (target_ids,),
            )
            missing_transcript_ids = [row[0] for row in cursor.fetchall()]

        connection.rollback()
        return (
            total_transcripts,
            joined_rows,
            missing_video_ids,
            missing_transcript_ids,
        )
    finally:
        connection.close()


def build_detail_rows(
    manifest: list[dict],
    joined_rows: list[dict],
) -> list[dict]:
    """Ghép position/title trong manifest với kết quả JOIN theo đúng playlist order."""

    database_rows_by_id = {}
    for row in joined_rows:
        database_rows_by_id.setdefault(row["video_id"], []).append(row)

    detail_rows = []
    for manifest_row in manifest:
        video_id = manifest_row["video_id"]
        for database_row in database_rows_by_id.get(video_id, []):
            detail_rows.append(
                {
                    "scope_version": SCOPE_VERSION,
                    "playlist_position": manifest_row["playlist_position"],
                    "video_id": video_id,
                    "manifest_title": manifest_row["title"],
                    **database_row,
                }
            )

    return detail_rows


def build_summary(
    total_transcripts: int,
    manifest: list[dict],
    detail_rows: list[dict],
    missing_video_ids: list[str],
    missing_transcript_ids: list[str],
) -> tuple[list[dict], list[str]]:
    """Tạo summary metrics và danh sách điều kiện validation bị vi phạm."""

    target_counts = Counter(row["video_id"] for row in detail_rows)
    duplicate_ids = [
        video_id for video_id, count in target_counts.items() if count > 1
    ]
    empty_raw_text = sum(
        row["transcript_length"] is None or row["transcript_length"] == 0
        for row in detail_rows
    )
    empty_language = sum(
        not row["language"] or not row["language"].strip()
        for row in detail_rows
    )
    lengths = [
        row["transcript_length"]
        for row in detail_rows
        if row["transcript_length"] is not None
    ]

    unique_target_transcripts = len(target_counts)
    metrics = {
        "scope_version": SCOPE_VERSION,
        "expected_total_transcripts": EXPECTED_TOTAL_TRANSCRIPTS,
        "actual_total_transcripts": total_transcripts,
        "expected_target_videos": len(manifest),
        "joined_target_rows": len(detail_rows),
        "unique_target_transcripts": unique_target_transcripts,
        "missing_video_metadata": len(missing_video_ids),
        "missing_target_transcripts": len(missing_transcript_ids),
        "duplicate_target_transcripts": len(duplicate_ids),
        "empty_target_raw_text": empty_raw_text,
        "empty_target_language": empty_language,
        "minimum_transcript_length": min(lengths) if lengths else "",
        "maximum_transcript_length": max(lengths) if lengths else "",
        "average_transcript_length": (
            round(sum(lengths) / len(lengths)) if lengths else ""
        ),
    }

    failures = []
    if total_transcripts != EXPECTED_TOTAL_TRANSCRIPTS:
        failures.append(
            f"Expected {EXPECTED_TOTAL_TRANSCRIPTS} total transcripts, "
            f"found {total_transcripts}"
        )
    if unique_target_transcripts != len(manifest):
        failures.append(
            f"Expected {len(manifest)} target transcripts, "
            f"found {unique_target_transcripts}"
        )
    if missing_video_ids:
        failures.append(f"Missing video metadata: {missing_video_ids}")
    if missing_transcript_ids:
        failures.append(f"Missing target transcripts: {missing_transcript_ids}")
    if duplicate_ids:
        failures.append(f"Duplicate target transcripts: {duplicate_ids}")
    if empty_raw_text:
        failures.append(f"Target transcripts with empty raw_text: {empty_raw_text}")
    if empty_language:
        failures.append(f"Target transcripts with empty language: {empty_language}")

    metrics["validation_status"] = "passed" if not failures else "failed"
    summary_rows = [
        {"metric": metric, "value": value}
        for metric, value in metrics.items()
    ]
    return summary_rows, failures


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Ghi CSV UTF-8 có BOM để có thể mở trực tiếp bằng Excel."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Chạy validation, ghi report và trả exit code khác 0 nếu có lỗi."""

    manifest = load_manifest()
    (
        total_transcripts,
        joined_rows,
        missing_video_ids,
        missing_transcript_ids,
    ) = fetch_validation_state(manifest)
    detail_rows = build_detail_rows(manifest, joined_rows)
    summary_rows, failures = build_summary(
        total_transcripts,
        manifest,
        detail_rows,
        missing_video_ids,
        missing_transcript_ids,
    )

    write_csv(SUMMARY_FILE, ["metric", "value"], summary_rows)
    write_csv(
        DETAIL_FILE,
        [
            "scope_version",
            "playlist_position",
            "video_id",
            "manifest_title",
            "postgres_title",
            "publish_date",
            "language",
            "transcript_length",
            "retrieved_at",
        ],
        detail_rows,
    )

    print(f"Total transcripts       : {total_transcripts}")
    print(f"Target manifest videos  : {len(manifest)}")
    print(f"Target joined rows      : {len(detail_rows)}")
    print(f"Missing video metadata  : {len(missing_video_ids)}")
    print(f"Missing transcripts     : {len(missing_transcript_ids)}")
    print(f"Validation status       : {'FAILED' if failures else 'PASSED'}")
    print(f"Summary report          : {SUMMARY_FILE}")
    print(f"Detail report           : {DETAIL_FILE}")

    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
