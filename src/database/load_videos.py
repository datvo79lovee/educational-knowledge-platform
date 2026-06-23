import json

from connection import get_connection


def load_jsonl(file_path):
    """
    Đọc file JSONL và trả về danh sách record.

    Input:
        E:/educational-knowledge-platform/data/silver/videos_clean.jsonl

    Output:
        list[dict]

    Mục đích:
        Tách logic đọc file khỏi logic database loading.
    """

    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def validate_record(record):
    """
    Kiểm tra record có đáp ứng schema videos hay không.

    Validation:
    - video_id không được NULL
    - source_id không được NULL
    - title không được NULL

    Trả về:
        True nếu hợp lệ.
        False nếu không hợp lệ.

    Mục đích:
        Tránh lỗi database constraint khi insert.
    """

    required_fields = [
        "video_id",
        "source_id",
        "title"
    ]

    for field in required_fields:

        if record.get(field) is None:
            return False

    return True


def insert_video(cursor, record):
    """
    Insert một video vào bảng videos.

    Sử dụng:
        ON CONFLICT (video_id) DO NOTHING

    để pipeline có thể chạy lại nhiều lần.

    Trả về:
        số dòng được insert.

    Mục đích:
        Tách biệt SQL logic khỏi orchestration logic.
    """

    query = """
    INSERT INTO videos (
        video_id,
        source_id,
        title,
        description,
        publish_date,
        duration_seconds,
        view_count
    )
    VALUES (
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s
    )
    ON CONFLICT (video_id)
    DO NOTHING;
    """

    cursor.execute(
        query,
        (
            record["video_id"],
            record["source_id"],
            record["title"],
            record["description"],
            record["publish_date"],
            record["duration_seconds"],
            record["view_count"]
        )
    )

    return cursor.rowcount


def load_videos(records):
    """
    Load toàn bộ video records vào PostgreSQL.

    Quy trình:
        1. Kết nối database.
        2. Validate record.
        3. Insert record.
        4. Commit transaction.
        5. In thống kê.

    Mục đích:
        Là entry point chính của Video Loading Pipeline.
    """

    conn = get_connection()

    cursor = conn.cursor()

    inserted_count = 0
    skipped_count = 0
    invalid_count = 0

    try:

        for record in records:

            if not validate_record(record):
                invalid_count += 1
                continue

            inserted = insert_video(
                cursor,
                record
            )

            if inserted > 0:
                inserted_count += 1
            else:
                skipped_count += 1

        conn.commit()

        print("\n===== LOAD SUMMARY =====")

        print(
            f"Inserted Records: {inserted_count}"
        )

        print(
            f"Skipped Records: {skipped_count}"
        )

        print(
            f"Invalid Records: {invalid_count}"
        )

    except Exception as e:

        conn.rollback()

        print(
            f"[ERROR] {e}"
        )

        raise

    finally:

        cursor.close()
        conn.close()


def main():
    """
    Entry point của chương trình.

    Quy trình:
        1. Đọc Silver Dataset.
        2. Gọi Video Loader.
    """

    file_path = (
        "E:/educational-knowledge-platform/data/silver/videos_clean.jsonl"
    )

    records = load_jsonl(
        file_path
    )

    print(
        f"Loaded {len(records)} records"
    )

    load_videos(records)


if __name__ == "__main__":
    main()