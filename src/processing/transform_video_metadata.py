import json
import re
from datetime import datetime


FILE_PATH = "data/bronze/video_metadata_raw.jsonl"
OUTPUT_PATH = "data/silver/videos_clean.jsonl"

def load_jsonl(file_path):
    """
    Đọc file JSONL và trả về list records.
    """

    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def parse_publish_date(published_at):
    """
    Convert:

    2026-06-16T16:05:10Z

    →

    2026-06-16
    """
    
    return datetime.strptime(
        published_at,
        "%Y-%m-%dT%H:%M:%SZ"
    ).date()



def parse_view_count(view_count):
    """
    Convert:

    "7437"

    →

    7437
    """

    return int(view_count)


def parse_duration_to_seconds(duration):
    """
    Convert ISO8601 duration thành tổng số giây.

    Ví dụ:

    PT4M
    → 240

    PT4M17S
    → 257

    PT1H18M14S
    → 4694
    """
    if duration == "P0D":
        return None
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration
    )

    # if match is None:
    #     print(f"Invalid duration: {duration}")
    #     return None

    hours, minutes, seconds = match.groups()

    hours = int(hours or 0)
    minutes = int(minutes or 0)
    seconds = int(seconds or 0)

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def transform_video_record(record):
    """
    Transform 1 raw metadata record
    thành record phù hợp với schema bảng videos.
    """

    snippet = record["snippet"]
    content_details = record["contentDetails"]
    statistics = record["statistics"]

    clean_record = {
        "video_id": record["id"],

        # Hiện tại chỉ có MIT OCW
        "source_id": 1,

        "title": snippet["title"],

        "description": snippet.get("description"),

        "publish_date": parse_publish_date(
            snippet["publishedAt"]
        ),

        "duration_seconds": parse_duration_to_seconds(
            content_details["duration"]
        ),

        "view_count": parse_view_count(
            statistics["viewCount"]
        )
    }

    return clean_record
def transform_all_records(records):

    clean_records = []

    for record in records:

        clean_record = transform_video_record(record)

        clean_records.append(clean_record)

    return clean_records

def write_jsonl(records, output_path):
    """
    Ghi list records ra file JSONL.
    """

    with open(output_path, "w", encoding="utf-8") as f:

        for record in records:

            json.dump(
                record,
                f,
                ensure_ascii=False,
                default=str
            )

            f.write("\n")
def main():

    records = load_jsonl(FILE_PATH)

    clean_records = transform_all_records(records)

    print(f"Clean records: {len(clean_records)}")

    print(clean_records[0])
    records = load_jsonl(FILE_PATH)

    clean_records = transform_all_records(records)

    write_jsonl(
        clean_records,
        OUTPUT_PATH
    )

    print(
        f"Silver records written: {len(clean_records)}"
    )

if __name__ == "__main__":
    main()