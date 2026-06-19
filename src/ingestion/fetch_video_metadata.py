import json
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.discovery import build
import os

load_dotenv()

youtube = build(
    "youtube",
    "v3",
    developerKey=os.getenv("YOUTUBE_API_KEY")
)

BRONZE_FILE = Path("data/bronze/videos_raw.jsonl")
VIDEO_METADATA_FILE = Path("data/bronze/video_metadata_raw.jsonl")


def extract_video_ids(file_path: Path) -> dict:
    """
    Đọc file videos_raw.jsonl và extract toàn bộ video_id.

    Input:
        data/bronze/videos_raw.jsonl

    Output:
        {
            "total_records": int,
            "video_ids": list[str],
            "missing_video_ids": int
        }
    """

    video_ids = []
    total_records = 0
    missing_video_ids = 0
    # mỗi dòng = 1 JSON object
    with open(file_path, "r", encoding="utf-8") as file:

        for line in file:
            total_records += 1

            # Parse JSON string -> Python dict
            record = json.loads(line)

            # Cấu trúc playlist item:
            #
            # snippet
            #   └── resourceId
            #         └── videoId
            #
            # Sử dụng .get() để tránh KeyError (lồng nhau)
            video_id = (
                record.get("snippet", {})
                .get("resourceId", {})
                .get("videoId")
            )

            if video_id:
                video_ids.append(video_id)
            else:
                missing_video_ids += 1

    return {
        "total_records": total_records,
        "video_ids": video_ids,
        "missing_video_ids": missing_video_ids,
    }


def deduplicate_video_ids(video_ids: list[str]) -> list[str]:
    """
    Loại bỏ video_id trùng lặp.

    Bronze vẫn giữ dữ liệu gốc.
    Tuy nhiên khi gọi Metadata API,
    chúng ta không muốn gọi nhiều lần cho cùng một video.
    """

    unique_video_ids = list(dict.fromkeys(video_ids))
    return unique_video_ids


def chunk_list(items: list, chunk_size: int):
    """
    Chia list lớn thành nhiều list nhỏ.
    """

    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def fetch_video_metadata(youtube, video_id_batch: list[str]) -> list[dict]:
    """
    Lấy metadata cho một batch video.

    Parameters
    ----------
    youtube :
        YouTube API client.

    video_id_batch : list[str]
        Danh sách tối đa 50 video IDs.

    Returns
    -------
    list[dict]
        Danh sách metadata video trả về từ API.
    """

    # API yêu cầu video IDs ở dạng:
    # id1,id2,id3,...
    video_ids_str = ",".join(video_id_batch)

    response = (
        youtube.videos()
        .list(
            part="snippet,contentDetails,statistics",
            id=video_ids_str
        )
        .execute()
    )

    return response["items"]


def save_jsonl(records: list[dict], output_path: Path):
    """
    Lưu danh sách records thành file JSONL.

    Mỗi dòng trong file là một JSON object.
    """

    with open(output_path, "w", encoding="utf-8") as file:

        for record in records:
            json.dump(
                record,
                file,
                ensure_ascii=False
            )

            file.write("\n")
    
def main():
    """
    Entry point của script.
    """

    result = extract_video_ids(BRONZE_FILE)
    video_ids = result["video_ids"]
    BATCH_SIZE = 50

    #deduplicate video_ids
    unique_video_ids = deduplicate_video_ids(video_ids)

    # Chia video IDs thành các batch 50 phần tử
    # vì videos().list() chỉ nhận tối đa 50 IDs/request
    batches = list(
            chunk_list(
                unique_video_ids,
                BATCH_SIZE
            )
        )
    
    print("\n=== DEDUPLICATION CHECK ===\n")

    print(f"Before dedup : {len(video_ids)}")
    print(f"After dedup  : {len(unique_video_ids)}")
    print(f"Duplicates   : {len(video_ids) - len(unique_video_ids)}")
    print("\n=== EXTRACTED ATTRIBUTES ===\n")

    print(f"Total records     : {result['total_records']}")
    print(f"Total video ids   : {len(result['video_ids'])}")
    print(f"Missing video ids : {result['missing_video_ids']}")
    
    print("\n=== BATCHING CHECK ===\n")
    
    print(f"Batch size    : {BATCH_SIZE}")
    print(f"Total batches : {len(batches)}")

    print(
    f"Videos in first batch : {len(batches[0])}"
)
    print(
    f"Videos in last batch : {len(batches[-1])}"
    )
    

    print("\n=== FETCHING VIDEO METADATA ===\n")
    all_metadata = []

    total_batches = len(batches)

    for batch_index, batch in enumerate(batches, start=1):

        metadata_items = fetch_video_metadata(
            youtube,
            batch
        )

        all_metadata.extend(metadata_items)

        print(
            f"[INFO] Batch {batch_index}/{total_batches} "
            f"completed - collected {len(metadata_items)} videos"
        )
    print("\n=== METADATA COLLECTION SUMMARY ===\n")

    print(f"Total batches processed : {total_batches}")
    print(f"Metadata records        : {len(all_metadata)}")

    # Lưu metadata đã thu thập được vào file JSONL

    save_jsonl(all_metadata, VIDEO_METADATA_FILE)

    print(
        f"\n[INFO] Metadata saved to: "
        f"{VIDEO_METADATA_FILE}"
    )

    with open(
        VIDEO_METADATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        line_count = sum(1 for _ in f)

    expected_records = len(all_metadata)

    print(
        f"[INFO] Expected records : {expected_records}"
    )

    print(
        f"[INFO] Records written  : {line_count}"
    )

    if expected_records != line_count:
        print("[ERROR] Record count mismatch!")

        
if __name__ == "__main__":
    main()
