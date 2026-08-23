import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from src.database.connection import (
    get_connection
)

from src.ingestion.fetch_transcripts import (
    fetch_transcript
)

from src.utils.jsonl import (
    append_jsonl,
    load_processed_video_ids
)

OUTPUT_FILE = Path(
    "data/bronze/transcripts_raw.jsonl"
)

CHECKPOINT_FILE = Path(
    "data/bronze/transcripts_checkpoint.jsonl"
)

PERMANENT_STATUSES = {
    "success",
    "no_transcript",
    "transcripts_disabled",
    "video_unavailable",
    "invalid_video_id"
}

BLOCK_STATUSES = {
    "too_many_requests",
    "request_blocked",
    "ip_blocked"
}


def utc_now():
    """
    Trả về thời gian hiện tại theo múi giờ UTC ở dạng chuỗi ISO.

    Thời gian này được dùng để ghi dấu mốc `fetched_at` cho transcript
    và `checked_at` cho checkpoint, giúp biết video được xử lý lúc nào.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def get_video_ids(limit=None):
    """
    Lấy danh sách `video_id` từ bảng `videos` trong PostgreSQL.

    Nếu truyền `limit`, hàm chỉ lấy tối đa số lượng video đó để test nhỏ
    trước khi chạy toàn bộ dataset. Kết quả được sắp xếp theo `video_id`
    để mỗi lần chạy lại có thứ tự ổn định.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            query = """
                SELECT video_id
                FROM videos
                ORDER BY video_id
            """

            params = None

            if limit is not None:
                query += """
                LIMIT %s
                """
                params = (
                    limit,
                )

            cur.execute(
                query,
                params
            )

            rows = cur.fetchall()

        return [
            row[0]
            for row in rows
        ]

    finally:
        conn.close()


def load_checkpoint_statuses(checkpoint_file):
    """
    Đọc file checkpoint và trả về trạng thái mới nhất của từng video.

    Checkpoint là file JSONL append-only: mỗi lần xử lý một video sẽ ghi
    thêm một dòng mới. Nếu một video xuất hiện nhiều lần, trạng thái cuối
    cùng trong file sẽ được dùng.
    """

    if not checkpoint_file.exists():
        return {}

    statuses = {}

    with checkpoint_file.open(
        "r",
        encoding="utf-8"
    ) as f:
        for line in f:
            try:
                record = json.loads(
                    line
                )
            except Exception:
                continue

            video_id = record.get(
                "video_id"
            )

            status = record.get(
                "status"
            )

            if video_id and status:
                statuses[video_id] = status

    return statuses


def load_completed_video_ids(output_file, checkpoint_file):
    """
    Tổng hợp các video đã xử lý xong để lần chạy sau bỏ qua.

    Nguồn 1 là file transcript output: video nào đã có transcript thì chắc
    chắn không cần fetch lại. Nguồn 2 là checkpoint: các trạng thái cố định
    như `no_transcript`, `transcripts_disabled`, `video_unavailable` cũng
    được xem là đã xử lý xong, vì retry thường không giúp ích.
    """

    completed_ids = load_processed_video_ids(
        output_file
    )

    checkpoint_statuses = load_checkpoint_statuses(
        checkpoint_file
    )

    for video_id, status in checkpoint_statuses.items():
        if status in PERMANENT_STATUSES:
            completed_ids.add(
                video_id
            )

    return completed_ids


def reconcile_transcript_state(output_file, checkpoint_file):
    """Load both state stores and warn when their success state disagrees.

    Transcript JSONL is authoritative for successful payloads. The checkpoint is
    authoritative for processing status.
    """
    payload_ids = load_processed_video_ids(output_file)
    checkpoint_statuses = load_checkpoint_statuses(checkpoint_file)
    checkpoint_success_ids = {
        video_id for video_id, status in checkpoint_statuses.items()
        if status == "success"
    }

    missing_payload_ids = checkpoint_success_ids - payload_ids
    missing_success_checkpoint_ids = payload_ids - checkpoint_success_ids

    if missing_payload_ids:
        print(
            "[WARNING] Checkpoint says success but transcript payload is "
            f"missing for {len(missing_payload_ids)} video(s)."
        )
    if missing_success_checkpoint_ids:
        print(
            "[WARNING] Transcript payload exists but latest checkpoint is not "
            f"success for {len(missing_success_checkpoint_ids)} video(s)."
        )

    return payload_ids, checkpoint_statuses


def build_ingestion_summary(video_ids, payload_ids, checkpoint_statuses):
    """Build cumulative metrics for the selected video queue."""
    selected_ids = set(video_ids)
    successful_ids = payload_ids & selected_ids
    permanent_unavailable_ids = {
        video_id for video_id, status in checkpoint_statuses.items()
        if video_id in selected_ids
        and status in PERMANENT_STATUSES
        and status != "success"
    }
    retryable_failure_ids = {
        video_id for video_id, status in checkpoint_statuses.items()
        if video_id in selected_ids and status not in PERMANENT_STATUSES
    }
    attempted_ids = successful_ids | permanent_unavailable_ids | retryable_failure_ids

    return {
        "total_videos": len(selected_ids),
        "cumulative_success_count": len(successful_ids),
        "permanently_unavailable": len(permanent_unavailable_ids),
        "retryable_failures": len(retryable_failure_ids),
        "not_attempted": len(selected_ids - attempted_ids),
    }


def write_checkpoint(video_id, status, error=None):
    """
    Ghi một dòng checkpoint cho video vừa được xử lý.

    Checkpoint lưu `video_id`, `status`, thời điểm kiểm tra và thông tin lỗi
    nếu có. Vì ghi append-only nên nếu chương trình bị tắt giữa chừng, những
    video đã đi qua vẫn còn dấu vết để hôm sau chạy tiếp.
    """

    record = {
        "video_id": video_id,
        "status": status,
        "checked_at": utc_now()
    }

    if error is not None:
        record["error_type"] = (
            error.__class__.__name__
        )
        record["error_message"] = str(
            error
        )

    append_jsonl(
        record,
        CHECKPOINT_FILE
    )


def classify_error(error):
    """
    Phân loại exception từ `youtube-transcript-api` thành status dễ xử lý.

    Các lỗi block/rate-limit như `IpBlocked`, `RequestBlocked`,
    `TooManyRequests` sẽ khiến pipeline dừng mềm để tránh gọi tiếp và bị
    chặn nặng hơn. Các lỗi cố định như video không có transcript sẽ được ghi
    checkpoint để không retry vô ích.
    """

    error_type = error.__class__.__name__
    message = str(error).lower()

    if (
        error_type == "IpBlocked"
        or "ip blocked" in message
    ):
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


def sleep_between_requests(min_delay, max_delay):
    """
    Nghỉ ngẫu nhiên giữa hai request YouTube.

    Khoảng nghỉ được chọn trong đoạn `[min_delay, max_delay]`. Delay ngẫu
    nhiên giúp giảm nhịp gọi đều đều, từ đó hạn chế khả năng bị YouTube đánh
    dấu là request tự động quá dày.
    """

    delay = random.uniform(
        min_delay,
        max_delay
    )

    print(
        f"[INFO] Sleeping {delay:.1f}s"
    )

    time.sleep(
        delay
    )


def should_stop_for_runtime(start_time, max_runtime_minutes):
    """
    Kiểm tra pipeline đã chạy quá thời lượng cho phép hay chưa.

    Nếu `max_runtime_minutes` là `None`, pipeline không bị giới hạn thời gian.
    Nếu đã vượt giới hạn, hàm trả về `True` để vòng lặp dừng sạch sẽ sau video
    hiện tại, thay vì bị ngắt đột ngột.
    """

    if max_runtime_minutes is None:
        return False

    elapsed_minutes = (
        time.time()
        - start_time
    ) / 60

    return elapsed_minutes >= max_runtime_minutes


def load_transcripts(
    limit=None,
    min_delay=8,
    max_delay=20,
    max_consecutive_failures=5,
    max_runtime_minutes=None
):
    """
    Hàm chính để fetch transcript từng video và ghi xuống JSONL.

    Quy trình:
    1. Lấy danh sách video từ PostgreSQL.
    2. Đọc output/checkpoint cũ để biết video nào đã xử lý.
    3. Với từng video chưa xong, gọi `fetch_transcript()`.
    4. Nếu thành công, ghi transcript vào `transcripts_raw.jsonl`.
    5. Luôn ghi checkpoint sau mỗi video để có thể resume.
    6. Dừng mềm khi gặp block/rate-limit hoặc quá nhiều lỗi liên tiếp.
    """

    video_ids = get_video_ids(
        limit=limit
    )

    payload_ids, checkpoint_statuses = reconcile_transcript_state(
        OUTPUT_FILE, CHECKPOINT_FILE
    )
    completed_ids = set(payload_ids)
    completed_ids.update(
        video_id for video_id, status in checkpoint_statuses.items()
        if status in PERMANENT_STATUSES
    )

    total = len(video_ids)
    run_success_count = 0
    skipped = 0
    failed = 0
    stopped = False
    stop_reason = None
    consecutive_failures = 0
    start_time = time.time()

    print(
        "\n===== TRANSCRIPT INGESTION START ====="
    )
    print(
        f"Videos loaded      : {total}"
    )
    print(
        f"Already completed : {len(completed_ids)}"
    )
    print(
        f"Output file       : {OUTPUT_FILE}"
    )
    print(
        f"Checkpoint file   : {CHECKPOINT_FILE}"
    )

    for index, video_id in enumerate(
        video_ids,
        start=1
    ):
        if video_id in completed_ids:
            skipped += 1
            continue

        if should_stop_for_runtime(
            start_time,
            max_runtime_minutes
        ):
            stopped = True
            stop_reason = "max_runtime_reached"
            break

        print(
            f"\n[INFO] {index}/{total} {video_id}"
        )

        try:
            record = fetch_transcript(
                video_id,
                raise_errors=True
            )

            if not record:
                failed += 1
                consecutive_failures += 1
                write_checkpoint(
                    video_id,
                    "fetch_failed"
                )
            else:
                record["fetched_at"] = utc_now()

                append_jsonl(
                    record,
                    OUTPUT_FILE
                )

                write_checkpoint(
                    video_id,
                    "success"
                )

                completed_ids.add(
                    video_id
                )

                run_success_count += 1
                consecutive_failures = 0

        except Exception as e:
            status = classify_error(
                e
            )

            write_checkpoint(
                video_id,
                status,
                error=e
            )

            print(
                f"[ERROR] {video_id} -> "
                f"{status}: {e}"
            )

            if status in PERMANENT_STATUSES:
                completed_ids.add(
                    video_id
                )
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            failed += 1

            if status in BLOCK_STATUSES:
                stopped = True
                stop_reason = status
                break

            if consecutive_failures >= max_consecutive_failures:
                stopped = True
                stop_reason = "max_consecutive_failures"
                break

        sleep_between_requests(
            min_delay,
            max_delay
        )
    
    payload_ids, checkpoint_statuses = reconcile_transcript_state(
        OUTPUT_FILE, CHECKPOINT_FILE
    )
    summary = build_ingestion_summary(video_ids, payload_ids, checkpoint_statuses)

    print("\n===== FINAL REPORT =====")

    print(f"Run success count          : {run_success_count}")
    print(f"Run skipped count          : {skipped}")
    print(f"Run failed count           : {failed}")
    print(f"Total videos               : {summary['total_videos']}")
    print(f"Cumulative success count   : {summary['cumulative_success_count']}")
    print(f"Permanently unavailable    : {summary['permanently_unavailable']}")
    print(f"Retryable failures         : {summary['retryable_failures']}")
    print(f"Not attempted              : {summary['not_attempted']}")
    print(f"Stopped                    : {stopped}")
    print(f"Reason                     : {stop_reason}")


def parse_args():
    """
    Định nghĩa các tham số dòng lệnh cho script.

    Các tham số này giúp chạy thử ít video bằng `--limit`, điều chỉnh delay
    bằng `--min-delay` và `--max-delay`, hoặc giới hạn thời gian chạy bằng
    `--max-runtime-minutes`.
    """

    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcripts into Bronze JSONL storage."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N videos from the videos table."
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=8,
        help="Minimum delay in seconds between videos."
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=20,
        help="Maximum delay in seconds between videos."
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=int,
        default=5,
        help="Stop after this many consecutive retryable failures."
    )
    parser.add_argument(
        "--max-runtime-minutes",
        type=float,
        default=None,
        help="Stop cleanly after this many minutes."
    )

    return parser.parse_args()


def main():
    """
    Entry point khi chạy file bằng `python -m src.database.load_transcripts --limit 50 --min-delay 20 --max-delay 60 --max-runtime-minutes 60` .

    Hàm này đọc tham số dòng lệnh, validate cấu hình delay, rồi gọi
     
    `load_transcripts()` để bắt đầu pipeline.
    """

    args = parse_args()

    if args.min_delay < 0:
        raise ValueError(
            "--min-delay must be >= 0"
        )

    if args.max_delay < args.min_delay:
        raise ValueError(
            "--max-delay must be >= --min-delay"
        )

    load_transcripts(
        limit=args.limit,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        max_consecutive_failures=args.max_consecutive_failures,
        max_runtime_minutes=args.max_runtime_minutes
    )


if __name__ == "__main__":
    main()
