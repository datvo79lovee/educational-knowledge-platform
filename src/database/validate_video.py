from connection import get_connection


def check_record_count(cursor):
    """
    Kiểm tra tổng số records trong bảng videos.
    """

    query = """
    SELECT COUNT(*)
    FROM videos;
    """

    cursor.execute(query)

    count = cursor.fetchone()[0]

    print("\n===== RECORD COUNT =====")
    print(f"Total Records: {count}")


def check_duplicate_videos(cursor):
    """
    Kiểm tra video_id bị duplicate.
    """

    query = """
    SELECT
        video_id,
        COUNT(*) AS duplicate_count
    FROM videos
    GROUP BY video_id
    HAVING COUNT(*) > 1;
    """

    cursor.execute(query)

    duplicates = cursor.fetchall()

    print("\n===== DUPLICATE CHECK =====")

    if not duplicates:
        print("PASS - No duplicate video_id found")
    else:
        print(f"FAIL - Found {len(duplicates)} duplicate video_ids")


def check_missing_title(cursor):
    """
    Kiểm tra title bị NULL.
    """

    query = """
    SELECT COUNT(*)
    FROM videos
    WHERE title IS NULL;
    """

    cursor.execute(query)

    count = cursor.fetchone()[0]

    print("\n===== MISSING TITLE =====")
    print(f"Missing Titles: {count}")


def check_missing_publish_date(cursor):
    """
    Kiểm tra publish_date bị NULL.
    """

    query = """
    SELECT COUNT(*)
    FROM videos
    WHERE publish_date IS NULL;
    """

    cursor.execute(query)

    count = cursor.fetchone()[0]

    print("\n===== MISSING PUBLISH DATE =====")
    print(f"Missing Publish Dates: {count}")


def check_missing_duration(cursor):
    """
    Kiểm tra duration_seconds bị NULL.
    """

    query = """
    SELECT COUNT(*)
    FROM videos
    WHERE duration_seconds IS NULL;
    """

    cursor.execute(query)

    count = cursor.fetchone()[0]

    print("\n===== MISSING DURATION =====")
    print(f"Missing Duration: {count}")


def check_foreign_key_integrity(cursor):
    """
    Kiểm tra mọi video đều tham chiếu
    tới source hợp lệ.
    """

    query = """
    SELECT COUNT(*)
    FROM videos v
    LEFT JOIN sources s
        ON v.source_id = s.source_id
    WHERE s.source_id IS NULL;
    """

    cursor.execute(query)

    count = cursor.fetchone()[0]

    print("\n===== FOREIGN KEY CHECK =====")

    if count == 0:
        print("PASS - All videos have valid sources")
    else:
        print(f"FAIL - {count} orphan records found")


def check_duration_statistics(cursor):
    """
    Kiểm tra phân bố duration.
    """

    query = """
    SELECT
        MIN(duration_seconds),
        MAX(duration_seconds),
        AVG(duration_seconds)
    FROM videos;
    """

    cursor.execute(query)

    min_duration, max_duration, avg_duration = cursor.fetchone()

    print("\n===== DURATION STATISTICS =====")

    print(f"Min Duration: {min_duration}")
    print(f"Max Duration: {max_duration}")
    print(f"Avg Duration: {round(avg_duration, 2)}")


def check_view_count_statistics(cursor):
    """
    Kiểm tra phân bố view_count.
    """

    query = """
    SELECT
        MIN(view_count),
        MAX(view_count),
        AVG(view_count)
    FROM videos;
    """

    cursor.execute(query)

    min_views, max_views, avg_views = cursor.fetchone()

    print("\n===== VIEW COUNT STATISTICS =====")

    print(f"Min Views: {min_views}")
    print(f"Max Views: {max_views}")
    print(f"Avg Views: {round(avg_views, 2)}")


def validate_videos():
    """
    Chạy toàn bộ validation sau khi load.
    """

    conn = get_connection()

    cursor = conn.cursor()

    try:

        check_record_count(cursor)

        check_duplicate_videos(cursor)

        check_missing_title(cursor)

        check_missing_publish_date(cursor)

        check_missing_duration(cursor)

        check_foreign_key_integrity(cursor)

        check_duration_statistics(cursor)

        check_view_count_statistics(cursor)

        print("\n===== VALIDATION COMPLETED =====")

    finally:

        cursor.close()

        conn.close()


def main():

    validate_videos()


if __name__ == "__main__":
    main()