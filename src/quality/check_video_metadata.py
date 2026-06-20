import json


FILE_PATH = "data/bronze/video_metadata_raw.jsonl"


def load_jsonl(file_path):
    """
    Đọc file JSONL.
    
    Mỗi dòng trong JSONL là một JSON object riêng,
    nên cần đọc từng dòng và convert bằng json.loads()
    """

    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def check_record_count(records):
    """
    Kiểm tra tổng số record đã ingest.
    """

    print(f"Total records: {len(records)}")


def check_first_record_keys(records):
    """
    Kiểm tra cấu trúc record đầu tiên.

    Mục đích:
    xác nhận API response có những field nào.
    """

    print(records[0].keys())


def check_duplicate_video_ids(records):
    """
    Video ID phải unique vì database dùng:

    video_id PRIMARY KEY
    """

    video_ids = []

    for record in records:
        video_ids.append(record["id"])

    total_ids = len(video_ids)
    unique_ids = len(set(video_ids))

    duplicate_count = total_ids - unique_ids

    print(f"Total video IDs: {total_ids}")
    print(f"Unique video IDs: {unique_ids}")
    print(f"Duplicate video IDs: {duplicate_count}")


def check_missing_objects(records):
    """
    Kiểm tra các object lớn trong API response.

    Ví dụ:
    record["snippet"]
    record["contentDetails"]
    record["statistics"]
    """

    missing_snippet = 0
    missing_content_details = 0
    missing_statistics = 0

    for record in records:

        if not record.get("snippet"):
            missing_snippet += 1

        if not record.get("contentDetails"):
            missing_content_details += 1

        if not record.get("statistics"):
            missing_statistics += 1


    print(f"Missing snippet: {missing_snippet}")
    print(f"Missing contentDetails: {missing_content_details}")
    print(f"Missing statistics: {missing_statistics}")



def check_missing_fields(records):
    """
    Kiểm tra các field cần mapping sang bảng videos.
    
    Mapping:

    snippet.title
    snippet.description
    snippet.publishedAt

    contentDetails.duration

    statistics.viewCount
    """

    missing_title = 0
    missing_description = 0
    missing_published_at = 0
    missing_duration = 0
    missing_view_count = 0


    for record in records:

        snippet = record.get("snippet", {})
        content_details = record.get("contentDetails", {})
        statistics = record.get("statistics", {})


        if not snippet.get("title"):
            missing_title += 1


        if not snippet.get("description"):
            missing_description += 1


        if not snippet.get("publishedAt"):
            missing_published_at += 1


        if not content_details.get("duration"):
            missing_duration += 1


        if not statistics.get("viewCount"):
            missing_view_count += 1



    print(f"Missing title: {missing_title}")
    print(f"Missing description: {missing_description}")
    print(f"Missing publishedAt: {missing_published_at}")
    print(f"Missing duration: {missing_duration}")
    print(f"Missing viewCount: {missing_view_count}")



def main():

    records = load_jsonl(FILE_PATH)

    check_record_count(records)

    check_first_record_keys(records)

    check_duplicate_video_ids(records)

    check_missing_objects(records)

    check_missing_fields(records)



if __name__ == "__main__":
    main()