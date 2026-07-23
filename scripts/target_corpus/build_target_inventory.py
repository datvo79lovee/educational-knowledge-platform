"""Tạo inventory, manifest và gap report cho corpus mục tiêu MIT 6.0001.

Script gọi YouTube Data API để lấy danh sách video trong playlist, sau đó chỉ đọc
PostgreSQL, Bronze transcript JSONL và checkpoint để đối chiếu trạng thái từng
video. Script không gọi transcript API và không tải nội dung transcript.

Manifest v1 được xem là snapshot bất biến. Nếu playlist hiện tại khác manifest đã
lưu, script dừng và yêu cầu tạo scope version mới thay vì ghi đè dữ liệu cũ.
"""

import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


# Các hằng số này khóa inventory vào đúng playlist và scope version đã chọn.
SCOPE_VERSION = "mit_60001_fall_2016_v1"
PLAYLIST_ID = "PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA"
EXPECTED_PLAYLIST_ITEMS = 38

# Bronze và checkpoint là nguồn kiểm tra trạng thái transcript hiện có.
TRANSCRIPT_FILE = Path("data/bronze/transcripts_raw.jsonl")
CHECKPOINT_FILE = Path("data/bronze/transcripts_checkpoint.jsonl")

# Ba file CSV kết quả được đặt chung trong bước quyết định phạm vi corpus.
REPORTS_DIR = Path("reports/04_scope_decision")

PERMANENT_UNAVAILABLE_STATUSES = {
    "no_transcript",
    "transcripts_disabled",
    "video_unavailable",
    "invalid_video_id",
}

RETRYABLE_STATUSES = {
    "fetch_failed",
    "ip_blocked",
    "request_blocked",
    "too_many_requests",
}


def create_youtube_client():
    """Tạo YouTube Data API client bằng API key trong environment hoặc file .env.

    ``developerKey`` dùng để xác thực request. ``cache_discovery=False`` tắt cache
    discovery document cục bộ, tránh tạo thêm file cache khi chạy script.
    """

    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY is missing from the environment or .env")
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def fetch_playlist_items(youtube) -> list[dict]:
    """Lấy toàn bộ item của playlist và giữ nguyên vị trí do YouTube trả về.

    ``youtube`` là client được tạo bởi :func:`create_youtube_client`. YouTube có thể
    chia kết quả thành nhiều trang, nên hàm tiếp tục request đến khi không còn
    ``nextPageToken``.
    """

    rows = []
    page_token = None

    while True:
        response = youtube.playlistItems().list(
            # snippet chứa title/position; contentDetails chứa videoId/ngày publish.
            part="snippet,contentDetails",
            # Chỉ đọc playlist MIT 6.0001 đã khóa ở đầu file.
            playlistId=PLAYLIST_ID,
            # API cho phép tối đa 50 item/trang; playlist dự kiến có 38 item.
            maxResults=50,
            # None ở request đầu; các request sau dùng token trang kế tiếp.
            pageToken=page_token,
        ).execute()

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            video_id = content_details.get("videoId") or snippet.get(
                "resourceId", {}
            ).get("videoId")

            if not video_id:
                raise ValueError(f"Playlist item has no video ID: {item.get('id')}")

            rows.append(
                {
                    "playlist_item_id": item.get("id", ""),
                    "playlist_id": PLAYLIST_ID,
                    "playlist_position": snippet.get("position"),
                    "video_id": video_id,
                    "playlist_title": snippet.get("title", ""),
                    "item_published_at": content_details.get(
                        "videoPublishedAt", snippet.get("publishedAt", "")
                    ),
                }
            )

        # Không có nextPageToken nghĩa là đã đọc hết playlist.
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    rows.sort(key=lambda row: row["playlist_position"])
    validate_playlist_items(rows)
    return rows


def validate_playlist_items(rows: list[dict]) -> None:
    """Từ chối snapshot thiếu item, trùng video hoặc sai thứ tự position.

    ``rows`` là danh sách item đã lấy từ API. Các kiểm tra này ngăn một response
    thiếu trang hoặc playlist bị thay đổi âm thầm đi vào manifest v1.
    """

    if len(rows) != EXPECTED_PLAYLIST_ITEMS:
        raise ValueError(
            f"Expected {EXPECTED_PLAYLIST_ITEMS} playlist items, found {len(rows)}"
        )

    video_ids = [row["video_id"] for row in rows]
    if len(set(video_ids)) != len(video_ids):
        duplicates = [
            video_id
            for video_id, count in Counter(video_ids).items()
            if count > 1
        ]
        raise ValueError(f"Duplicate video IDs in playlist: {duplicates}")

    positions = [row["playlist_position"] for row in rows]
    expected_positions = list(range(EXPECTED_PLAYLIST_ITEMS))
    if positions != expected_positions:
        raise ValueError(
            f"Unexpected playlist positions: expected {expected_positions}, got {positions}"
        )


def load_bronze_transcript_ids() -> set[str]:
    """Đọc tập video ID đã có payload transcript thành công trong Bronze."""

    transcript_ids = set()
    with TRANSCRIPT_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid transcript JSON at line {line_number}: {error}"
                ) from error

            video_id = payload.get("video_id")
            if not video_id:
                raise ValueError(f"Transcript line {line_number} has no video_id")
            transcript_ids.add(video_id)
    return transcript_ids


def load_latest_checkpoint_statuses() -> dict[str, str]:
    """Lấy trạng thái checkpoint mới nhất của mỗi video.

    Checkpoint là file append-only nên một video có thể xuất hiện nhiều lần. Gán
    lại theo thứ tự dòng khiến record cuối cùng trở thành trạng thái hiện tại.
    """

    latest_statuses = {}
    with CHECKPOINT_FILE.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid checkpoint JSON at line {line_number}: {error}"
                ) from error

            video_id = record.get("video_id")
            status = record.get("status")
            if video_id and status:
                latest_statuses[video_id] = status
    return latest_statuses


def fetch_postgres_state(video_ids: list[str]) -> tuple[dict[str, dict], set[str]]:
    """Đọc metadata video và sự hiện diện transcript mà không sửa PostgreSQL.

    ``video_ids`` chỉ gồm ID lấy từ target playlist. Hàm trả về hai phần: dictionary
    metadata theo video ID và tập ID đã có trong bảng ``transcripts``.
    """

    connection = get_connection()
    try:
        # Read-only chặn các thao tác ghi ngoài ý muốn trong phiên đối chiếu.
        connection.set_session(readonly=True, autocommit=False)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT video_id, title, publish_date, duration_seconds
                FROM videos
                WHERE video_id = ANY(%s)
                """,
                # ``ANY(%s)`` nhận toàn bộ list dưới dạng một PostgreSQL array.
                (video_ids,),
            )
            videos = {
                row[0]: {
                    "postgres_title": row[1],
                    "publish_date": row[2],
                    "duration_seconds": row[3],
                }
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT DISTINCT video_id
                FROM transcripts
                WHERE video_id = ANY(%s)
                """,
                (video_ids,),
            )
            transcript_ids = {row[0] for row in cursor.fetchall()}

        connection.rollback()
        return videos, transcript_ids
    finally:
        connection.close()


def classify_target_status(
    in_bronze: bool,
    in_postgres: bool,
    checkpoint_status: str,
) -> tuple[str, bool, bool]:
    """Phân loại trạng thái và quyết định video có được đưa vào queue fetch không.

    Tham số:
    - ``in_bronze``: đã có raw payload thành công hay chưa.
    - ``in_postgres``: đã có transcript trong PostgreSQL hay chưa.
    - ``checkpoint_status``: kết quả xử lý gần nhất, rỗng nếu chưa từng thử.

    Giá trị trả về lần lượt là ``target_status``, ``fetch_candidate`` và
    ``requires_manual_review``.
    """

    if in_bronze and in_postgres:
        return "already_available", False, False
    if in_bronze and not in_postgres:
        return "bronze_payload_not_loaded", False, True
    if in_postgres and not in_bronze:
        return "postgres_without_bronze_payload", False, True
    if checkpoint_status == "success":
        return "checkpoint_success_missing_payload", False, True
    if checkpoint_status in PERMANENT_UNAVAILABLE_STATUSES:
        return checkpoint_status, False, False
    if checkpoint_status in RETRYABLE_STATUSES:
        return "retryable_failure", True, False
    if checkpoint_status:
        return "unknown_checkpoint_status", False, True
    return "not_attempted", True, False


def build_inventory(playlist_rows: list[dict]) -> list[dict]:
    """Ghép trạng thái playlist, PostgreSQL, Bronze và checkpoint theo từng video."""

    video_ids = [row["video_id"] for row in playlist_rows]
    bronze_ids = load_bronze_transcript_ids()
    checkpoint_statuses = load_latest_checkpoint_statuses()
    postgres_videos, postgres_transcript_ids = fetch_postgres_state(video_ids)

    inventory = []
    for row in playlist_rows:
        video_id = row["video_id"]
        postgres_video = postgres_videos.get(video_id, {})
        in_bronze = video_id in bronze_ids
        in_postgres = video_id in postgres_transcript_ids
        checkpoint_status = checkpoint_statuses.get(video_id, "")
        # Chỉ not_attempted/retryable_failure được phép trở thành fetch candidate.
        target_status, fetch_candidate, requires_review = classify_target_status(
            in_bronze, in_postgres, checkpoint_status
        )

        inventory.append(
            {
                **row,
                "video_in_postgres": video_id in postgres_videos,
                "postgres_title": postgres_video.get("postgres_title", ""),
                "publish_date": postgres_video.get("publish_date", ""),
                "duration_seconds": postgres_video.get("duration_seconds", ""),
                "transcript_in_bronze": in_bronze,
                "transcript_in_postgres": in_postgres,
                "latest_checkpoint_status": checkpoint_status,
                "target_status": target_status,
                "fetch_candidate": fetch_candidate,
                "requires_manual_review": requires_review,
            }
        )

    missing_metadata = [
        row["video_id"] for row in inventory if not row["video_in_postgres"]
    ]
    if missing_metadata:
        raise ValueError(
            f"Target videos missing from PostgreSQL videos: {missing_metadata}"
        )
    return inventory


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Ghi danh sách dictionary thành CSV UTF-8 có BOM để Excel đọc đúng tiếng Việt."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(inventory: list[dict]) -> None:
    """Ghi inventory, gap report và manifest bất biến của scope hiện tại.

    ``inventory`` chứa đủ 38 video. Gap report loại các video đã sẵn sàng; manifest
    giữ toàn bộ video thuộc phạm vi, không phụ thuộc trạng thái transcript.
    """

    inventory_fields = list(inventory[0].keys())
    gap_rows = [row for row in inventory if row["target_status"] != "already_available"]
    manifest_rows = [
        {
            "scope_version": SCOPE_VERSION,
            "playlist_id": row["playlist_id"],
            "playlist_position": str(row["playlist_position"]),
            "video_id": row["video_id"],
            "title": row["playlist_title"],
            "included": "True",
        }
        for row in inventory
    ]

    write_csv(
        REPORTS_DIR / "target_playlist_inventory.csv",
        inventory_fields,
        inventory,
    )
    write_csv(
        REPORTS_DIR / "target_gap_report.csv",
        inventory_fields,
        gap_rows,
    )
    manifest_path = REPORTS_DIR / "target_manifest.csv"
    manifest_fields = [
        "scope_version",
        "playlist_id",
        "playlist_position",
        "video_id",
        "title",
        "included",
    ]

    if manifest_path.exists():
        # Manifest v1 đã tồn tại chỉ được xác nhận, không được cập nhật tại chỗ.
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as file:
            existing_manifest = list(csv.DictReader(file))
        if existing_manifest != manifest_rows:
            raise RuntimeError(
                "Existing target manifest differs from the current playlist. "
                "Create a new scope version instead of overwriting v1."
            )
    else:
        write_csv(manifest_path, manifest_fields, manifest_rows)

    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    print(f"Manifest SHA-256   : {manifest_hash}")


def main() -> None:
    """Chạy lần lượt: đọc playlist, đối chiếu dữ liệu, ghi report và in tổng kết."""

    youtube = create_youtube_client()
    playlist_rows = fetch_playlist_items(youtube)
    inventory = build_inventory(playlist_rows)
    write_reports(inventory)

    statuses = Counter(row["target_status"] for row in inventory)
    print(f"Playlist items     : {len(inventory)}")
    print(f"Unique video IDs   : {len({row['video_id'] for row in inventory})}")
    print(
        "Playlist positions: "
        f"{inventory[0]['playlist_position']}..{inventory[-1]['playlist_position']}"
    )
    for status, count in sorted(statuses.items()):
        print(f"Status {status:<34}: {count}")
    print(
        "Fetch candidates   : "
        f"{sum(bool(row['fetch_candidate']) for row in inventory)}"
    )
    print(
        "Manual review      : "
        f"{sum(bool(row['requires_manual_review']) for row in inventory)}"
    )


if __name__ == "__main__":
    main()
