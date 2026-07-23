"""Thu transcript chỉ cho corpus mục tiêu MIT 6.0001.

Mặc định script chạy ở planning mode: kiểm tra manifest, dựng queue và tạo report
nhưng không gọi transcript API. Chỉ khi truyền ``--execute``, script mới gửi
request và ghi nối tiếp vào Bronze JSONL cùng checkpoint dùng chung.

Script luôn kiểm tra video thuộc manifest v1 và đã được gap report cho phép. Vì
vậy một tham số sai không thể vô tình mở rộng crawler ra toàn bộ channel.
"""

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.fetch_transcripts import fetch_transcript
from src.utils.jsonl import append_jsonl, load_processed_video_ids


# Các hằng số này khóa phạm vi crawler vào đúng snapshot MIT 6.0001 đã duyệt.
# Muốn đổi playlist hoặc thêm video phải tạo scope version mới, không sửa ngầm v1.
SCOPE_VERSION = "mit_60001_fall_2016_v1"
PLAYLIST_ID = "PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA"
EXPECTED_MANIFEST_ROWS = 38

# Manifest xác định toàn bộ corpus; gap report xác định phần được phép gọi API.
MANIFEST_FILE = Path("reports/04_scope_decision/target_manifest.csv")
GAP_FILE = Path("reports/04_scope_decision/target_gap_report.csv")

# Payload thành công và lịch sử xử lý tiếp tục dùng source of truth hiện có.
# Không tạo một bản raw transcript thứ hai chỉ dành cho MIT 6.0001.
TRANSCRIPT_FILE = Path("data/bronze/transcripts_raw.jsonl")
CHECKPOINT_FILE = Path("data/bronze/transcripts_checkpoint.jsonl")
REPORTS_DIR = Path("reports/05_target_corpus")

PERMANENT_STATUSES = {
    "success",
    "no_transcript",
    "transcripts_disabled",
    "video_unavailable",
    "invalid_video_id",
}

BLOCK_STATUSES = {
    "ip_blocked",
    "request_blocked",
    "too_many_requests",
}

RETRYABLE_STATUSES = BLOCK_STATUSES | {"fetch_failed"}


def utc_now() -> str:
    """Tạo timestamp UTC ISO-8601 để truy vết thời điểm fetch/checkpoint."""

    return datetime.now(timezone.utc).isoformat()


def parse_boolean(value: str) -> bool:
    """Đọc boolean trong CSV một cách nghiêm ngặt thay vì coi chuỗi là truthy."""

    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Expected boolean value, found: {value!r}")


def load_manifest() -> list[dict]:
    """Đọc manifest và dừng ngay nếu phạm vi không còn đúng bản v1.

    Các kiểm tra gồm số dòng, video trùng, position, scope version, playlist ID và
    cờ included. Đây là lớp bảo vệ đầu tiên trước khi dựng queue.
    """

    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Target manifest does not exist: {MANIFEST_FILE}")

    with MANIFEST_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if len(rows) != EXPECTED_MANIFEST_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_MANIFEST_ROWS} manifest rows, found {len(rows)}"
        )

    # Một video lặp trong manifest có thể bị fetch hai lần, nên duplicate là lỗi.
    video_ids = [row["video_id"] for row in rows]
    if len(set(video_ids)) != len(video_ids):
        raise ValueError("Target manifest contains duplicate video IDs")

    # Position 0..37 đảm bảo snapshot vẫn là đúng playlist 38 items đã duyệt.
    positions = sorted(int(row["playlist_position"]) for row in rows)
    if positions != list(range(EXPECTED_MANIFEST_ROWS)):
        raise ValueError(f"Target manifest has invalid playlist positions: {positions}")

    for row in rows:
        if row["scope_version"] != SCOPE_VERSION:
            raise ValueError(
                f"Unsupported scope version for {row['video_id']}: "
                f"{row['scope_version']}"
            )
        if row["playlist_id"] != PLAYLIST_ID:
            raise ValueError(
                f"Video {row['video_id']} belongs to an unexpected playlist"
            )
        if not parse_boolean(row["included"]):
            raise ValueError(f"Manifest video is not included: {row['video_id']}")

        row["playlist_position"] = int(row["playlist_position"])

    return sorted(rows, key=lambda row: row["playlist_position"])


def load_gap_candidates(manifest_ids: set[str]) -> set[str]:
    """Chỉ lấy video đã được gap report đánh dấu cho phép fetch.

    Manifest trả lời "video nào thuộc scope". Gap report trả lời "video nào trong
    scope hiện cần request". Crawler yêu cầu đồng thời cả hai điều kiện.
    """

    if not GAP_FILE.exists():
        raise FileNotFoundError(f"Target gap report does not exist: {GAP_FILE}")

    with GAP_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    gap_ids = {row["video_id"] for row in rows}
    outside_scope = gap_ids - manifest_ids
    if outside_scope:
        raise ValueError(
            f"Gap report contains video IDs outside the manifest: {sorted(outside_scope)}"
        )

    candidates = {
        row["video_id"]
        for row in rows
        if parse_boolean(row["fetch_candidate"])
    }
    if not candidates <= manifest_ids:
        raise ValueError("Fetch candidates are not a subset of the target manifest")
    return candidates


def load_latest_checkpoint_records() -> dict[str, dict]:
    """Lấy trạng thái cuối cùng của mỗi video từ checkpoint append-only.

    Một video có thể xuất hiện nhiều lần do retry. Dòng cuối cùng mới đại diện cho
    trạng thái hiện tại; các dòng cũ vẫn được giữ để audit lịch sử.
    """

    if not CHECKPOINT_FILE.exists():
        return {}

    records = {}
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
                records[video_id] = record
    return records


def classify_error(error: Exception) -> str:
    """Chuẩn hóa exception của youtube-transcript-api thành status ổn định.

    Status ổn định giúp lần chạy sau biết lỗi nào không nên retry và lỗi nào cần
    dừng toàn bộ queue để tránh làm tình trạng block nặng hơn.
    """

    error_type = error.__class__.__name__
    message = str(error).lower()

    if error_type == "IpBlocked" or "ip blocked" in message:
        return "ip_blocked"
    if (
        error_type == "RequestBlocked"
        or "request blocked" in message
        or "blocked" in message
    ):
        return "request_blocked"
    if (
        error_type == "TooManyRequests"
        or "too many requests" in message
        or "429" in message
    ):
        return "too_many_requests"
    if error_type == "NoTranscriptFound":
        return "no_transcript"
    if error_type == "TranscriptsDisabled":
        return "transcripts_disabled"
    if error_type == "VideoUnavailable":
        return "video_unavailable"
    if error_type == "InvalidVideoId":
        return "invalid_video_id"
    return "fetch_failed"


def write_checkpoint(video_id: str, status: str, error: Exception | None = None) -> None:
    """Ghi nối tiếp checkpoint mới và không sửa lịch sử cũ.

    scope_version và pipeline giúp phân biệt request của target crawler với các
    lần crawl channel trước đây.
    """

    record = {
        "video_id": video_id,
        "status": status,
        "checked_at": utc_now(),
        "scope_version": SCOPE_VERSION,
        "pipeline": "target_corpus",
    }
    if error is not None:
        record["error_type"] = error.__class__.__name__
        record["error_message"] = str(error)
    append_jsonl(record, CHECKPOINT_FILE)


def select_queue(
    manifest: list[dict],
    reviewed_candidate_ids: set[str],
    payload_ids: set[str],
    checkpoint_records: dict[str, dict],
    requested_video_ids: list[str] | None,
    limit: int | None,
) -> list[dict]:
    """Dựng queue theo playlist position và áp dụng toàn bộ guardrail.

    Quy tắc lọc theo thứ tự:
    1. ID do người dùng truyền phải thuộc manifest.
    2. ID đó phải nằm trong reviewed gap candidates.
    3. Video đã có Bronze payload bị bỏ qua để hỗ trợ resume.
    4. Status cố định bị bỏ qua để không request vô ích.
    5. ``limit`` chỉ cắt queue sau khi mọi guardrail đã chạy.
    """

    manifest_by_id = {row["video_id"]: row for row in manifest}

    if requested_video_ids:
        requested_set = set(requested_video_ids)
        outside_manifest = requested_set - set(manifest_by_id)
        if outside_manifest:
            raise ValueError(
                f"Requested video IDs outside the target manifest: "
                f"{sorted(outside_manifest)}"
            )
        outside_reviewed_gap = requested_set - reviewed_candidate_ids
        if outside_reviewed_gap:
            raise ValueError(
                f"Requested video IDs are not reviewed fetch candidates: "
                f"{sorted(outside_reviewed_gap)}"
            )
        allowed_ids = requested_set
    else:
        allowed_ids = reviewed_candidate_ids

    # Duyệt manifest đã sort theo position để thứ tự queue luôn tái lập được.
    queue = []
    for row in manifest:
        video_id = row["video_id"]
        if video_id not in allowed_ids or video_id in payload_ids:
            continue

        latest_status = checkpoint_records.get(video_id, {}).get("status", "")
        if latest_status in PERMANENT_STATUSES:
            continue
        queue.append(row)

    if limit is not None:
        queue = queue[:limit]
    return queue


def sleep_between_requests(min_delay: float, max_delay: float) -> None:
    """Nghỉ ngẫu nhiên trong khoảng cấu hình để giảm nhịp request liên tục."""

    delay = random.uniform(min_delay, max_delay)
    print(f"Sleeping {delay:.1f}s")
    time.sleep(delay)


def runtime_exceeded(start_time: float, max_runtime_minutes: float | None) -> bool:
    """Cho phép phiên chạy dừng mềm sau thời lượng tối đa đã cấu hình."""

    if max_runtime_minutes is None:
        return False
    return (time.time() - start_time) / 60 >= max_runtime_minutes


def derive_acquisition_status(
    video_id: str,
    payload_ids: set[str],
    checkpoint_records: dict[str, dict],
) -> str:
    """Suy ra trạng thái hiện tại từ Bronze payload và checkpoint mới nhất."""

    # Bronze payload là bằng chứng chính của một lần fetch thành công.
    if video_id in payload_ids:
        return "payload_available"

    latest_status = checkpoint_records.get(video_id, {}).get("status", "")
    if latest_status == "success":
        return "checkpoint_success_missing_payload"
    if latest_status in PERMANENT_STATUSES:
        return latest_status
    if latest_status in RETRYABLE_STATUSES:
        return "retryable_failure"
    if latest_status:
        return "unknown_checkpoint_status"
    return "not_attempted"


def write_reports(manifest: list[dict]) -> dict[str, int]:
    """Tạo report cho đủ 38 video từ trạng thái Bronze/checkpoint hiện tại.

    Report được tạo cả trong planning mode để có baseline trước khi request thật.
    Sau mỗi phiên execute, cùng hàm này cập nhật coverage mới nhất.
    """

    payload_ids = load_processed_video_ids(TRANSCRIPT_FILE)
    checkpoint_records = load_latest_checkpoint_records()
    rows = []

    for manifest_row in manifest:
        video_id = manifest_row["video_id"]
        checkpoint = checkpoint_records.get(video_id, {})
        rows.append(
            {
                "scope_version": SCOPE_VERSION,
                "playlist_position": manifest_row["playlist_position"],
                "video_id": video_id,
                "title": manifest_row["title"],
                "payload_in_bronze": video_id in payload_ids,
                "latest_checkpoint_status": checkpoint.get("status", ""),
                "last_checked_at": checkpoint.get("checked_at", ""),
                "acquisition_status": derive_acquisition_status(
                    video_id, payload_ids, checkpoint_records
                ),
            }
        )

    status_counts = Counter(row["acquisition_status"] for row in rows)
    summary_rows = [
        {"metric": "target_videos", "value": len(rows)},
        {
            "metric": "payload_available",
            "value": status_counts.get("payload_available", 0),
        },
        {
            "metric": "not_attempted",
            "value": status_counts.get("not_attempted", 0),
        },
        {
            "metric": "permanently_unavailable",
            "value": sum(
                status_counts.get(status, 0)
                for status in PERMANENT_STATUSES
                if status != "success"
            ),
        },
        {
            "metric": "retryable_failures",
            "value": status_counts.get("retryable_failure", 0),
        },
        {
            "metric": "requires_manual_review",
            "value": status_counts.get("checkpoint_success_missing_payload", 0)
            + status_counts.get("unknown_checkpoint_status", 0),
        },
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORTS_DIR / "acquisition_status.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (REPORTS_DIR / "acquisition_summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    return dict(status_counts)


def execute_queue(
    queue: list[dict],
    min_delay: float,
    max_delay: float,
    max_consecutive_failures: int,
    max_runtime_minutes: float | None,
) -> tuple[int, int, str | None]:
    """Chạy queue đã duyệt và dừng an toàn khi gặp block hoặc quá nhiều lỗi.

    Trình tự ghi khi thành công là payload trước, checkpoint sau. Nếu tiến trình
    dừng giữa hai bước, Bronze payload vẫn là nguồn sự thật và lần chạy sau sẽ bỏ
    qua video đó thay vì fetch lại.
    """

    success_count = 0
    failed_count = 0
    consecutive_failures = 0
    stop_reason = None
    start_time = time.time()

    for index, row in enumerate(queue, start=1):
        if runtime_exceeded(start_time, max_runtime_minutes):
            stop_reason = "max_runtime_reached"
            break

        video_id = row["video_id"]
        print(
            f"Fetching {index}/{len(queue)} "
            f"position={row['playlist_position']} video_id={video_id}"
        )

        try:
            # Wrapper hiện tại của project lấy transcript ưu tiên tiếng Anh và
            # trả lại metadata language, is_generated cùng toàn bộ segments.
            record = fetch_transcript(video_id, raise_errors=True)
            if not record:
                raise RuntimeError("Transcript fetch returned no payload")

            # Chỉ append khi đã nhận payload hợp lệ; không ghi record giả cho lỗi.
            record["fetched_at"] = utc_now()
            append_jsonl(record, TRANSCRIPT_FILE)
            write_checkpoint(video_id, "success")
            success_count += 1
            consecutive_failures = 0

        except Exception as error:
            status = classify_error(error)
            write_checkpoint(video_id, status, error)
            failed_count += 1
            print(f"Fetch failed for {video_id}: {status}: {error}")

            # Lỗi cố định thuộc riêng video nên không tăng chuỗi lỗi hệ thống.
            if status in PERMANENT_STATUSES:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            # Khi bị block phải dừng ngay, không tiếp tục thử các video còn lại.
            if status in BLOCK_STATUSES:
                stop_reason = status
                break
            if consecutive_failures >= max_consecutive_failures:
                stop_reason = "max_consecutive_failures"
                break

        if index < len(queue):
            sleep_between_requests(min_delay, max_delay)

    return success_count, failed_count, stop_reason


def parse_args() -> argparse.Namespace:
    """Khai báo tham số dòng lệnh cho planning mode và execute mode."""

    parser = argparse.ArgumentParser(
        description="Fetch transcripts only for MIT 6.0001 manifest candidates."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Bật request transcript và ghi Bronze/checkpoint. Nếu không truyền, "
            "script chỉ dựng queue và report."
        ),
    )
    parser.add_argument(
        "--video-id",
        action="append",
        dest="video_ids",
        help=(
            "Chỉ chọn một video ID đã được gap report duyệt. Có thể lặp tham số "
            "để chọn nhiều video."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ xử lý tối đa N video đầu tiên sau khi queue đã được lọc.",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=8,
        help="Số giây nghỉ tối thiểu giữa hai request; mặc định 8.",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=20,
        help="Số giây nghỉ tối đa giữa hai request; mặc định 20.",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=5,
        help="Dừng sau N lỗi retryable liên tiếp; mặc định 5.",
    )
    parser.add_argument(
        "--max-runtime-minutes",
        type=float,
        default=None,
        help="Dừng mềm sau N phút; mặc định không giới hạn thời lượng.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Từ chối cấu hình vô nghĩa trước khi dựng queue hoặc gọi API."""

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than zero")
    if args.min_delay < 0:
        raise ValueError("--min-delay must be zero or greater")
    if args.max_delay < args.min_delay:
        raise ValueError("--max-delay must be greater than or equal to --min-delay")
    if args.max_consecutive_failures <= 0:
        raise ValueError("--max-consecutive-failures must be greater than zero")
    if args.max_runtime_minutes is not None and args.max_runtime_minutes <= 0:
        raise ValueError("--max-runtime-minutes must be greater than zero")


def main() -> None:
    """Điều phối validate scope, dựng queue, planning hoặc execute và report."""

    args = parse_args()
    validate_args(args)

    manifest = load_manifest()
    manifest_ids = {row["video_id"] for row in manifest}
    reviewed_candidates = load_gap_candidates(manifest_ids)
    payload_ids = load_processed_video_ids(TRANSCRIPT_FILE)
    checkpoint_records = load_latest_checkpoint_records()
    queue = select_queue(
        manifest,
        reviewed_candidates,
        payload_ids,
        checkpoint_records,
        args.video_ids,
        args.limit,
    )

    print(f"Scope version      : {SCOPE_VERSION}")
    print(f"Manifest videos    : {len(manifest)}")
    print(f"Reviewed candidates: {len(reviewed_candidates)}")
    print(f"Queued videos      : {len(queue)}")
    for row in queue:
        print(
            f"  {row['playlist_position']:>2} "
            f"{row['video_id']} {row['title']}"
        )

    # Planning mode là mặc định an toàn: không có transcript request hoặc raw write.
    if not args.execute:
        statuses = write_reports(manifest)
        print("Planning mode: no transcript requests were made.")
        for status, count in sorted(statuses.items()):
            print(f"Status {status:<34}: {count}")
        return

    success_count, failed_count, stop_reason = execute_queue(
        queue,
        args.min_delay,
        args.max_delay,
        args.max_consecutive_failures,
        args.max_runtime_minutes,
    )
    statuses = write_reports(manifest)

    print(f"Run success        : {success_count}")
    print(f"Run failed         : {failed_count}")
    print(f"Stop reason        : {stop_reason}")
    for status, count in sorted(statuses.items()):
        print(f"Status {status:<34}: {count}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"ERROR: {error}") from error
