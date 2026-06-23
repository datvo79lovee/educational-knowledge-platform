from connection import get_connection


SOURCES = [
    {
        "source_name": "MIT OpenCourseWare",
        "channel_id": "UCEBb1b_L6zDS3xTUrIALZOw",
        "source_url": "https://www.youtube.com/@mitocw"
    }
]


def validate_source(source):
    """
    Kiểm tra source có đầy đủ thông tin bắt buộc.
    """

    required_fields = [
        "source_name",
        "channel_id"
    ]

    for field in required_fields:

        if not source.get(field):
            return False

    return True


def insert_source(cursor, source):
    """
    Insert source vào bảng sources.

    Nếu channel_id đã tồn tại thì bỏ qua.
    """

    query = """
    INSERT INTO sources (
        source_name,
        channel_id,
        source_url
    )
    VALUES (
        %s,
        %s,
        %s
    )
    ON CONFLICT (channel_id)
    DO NOTHING;
    """

    cursor.execute(
        query,
        (
            source["source_name"],
            source["channel_id"],
            source["source_url"]
        )
    )

    return cursor.rowcount


def load_sources():
    """
    Load seed data vào bảng sources.
    """

    conn = get_connection()
    cursor = conn.cursor()

    inserted_count = 0
    skipped_count = 0

    try:

        for source in SOURCES:

            if not validate_source(source):
                continue

            inserted = insert_source(
                cursor,
                source
            )

            if inserted > 0:
                inserted_count += 1
            else:
                skipped_count += 1

        conn.commit()

        print("\n===== SOURCE LOAD SUMMARY =====")
        print(f"Inserted Sources: {inserted_count}")
        print(f"Skipped Sources: {skipped_count}")

    except Exception as e:

        conn.rollback()

        print(f"[ERROR] {e}")

        raise

    finally:

        cursor.close()
        conn.close()


def main():

    load_sources()


if __name__ == "__main__":
    main()