import json

PLAYLIST_FILE = "data/bronze/videos_raw.jsonl"

METADATA_FILE = "data/bronze/video_metadata_raw.jsonl"


def load_jsonl(file_path):
    """
    Đọc file JSONL và trả về list records.
    """

    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def extract_playlist_video_ids(records):
    """
    Lấy toàn bộ video_id từ playlist ingestion layer.
    """

    video_ids = set()


    for record in records:

        video_id = (
            record
            .get("snippet", {})
            .get("resourceId", {})
            .get("videoId")
        )


        if video_id:
            video_ids.add(video_id)


    return video_ids


def extract_playlist_video_ids(records):
    """
    Lấy toàn bộ video_id từ playlist ingestion layer.
    """

    video_ids = set()


    for record in records:

        video_id = (
            record
            .get("snippet", {})
            .get("resourceId", {})
            .get("videoId")
        )


        if video_id:
            video_ids.add(video_id)


    return video_ids

#Extract video IDs từ metadata layer
def extract_metadata_video_ids(records):
    """
    Lấy video_id từ Videos API metadata response.
    """

    video_ids = set()


    for record in records:

        video_id = record.get("id")


        if video_id:
            video_ids.add(video_id)


    return video_ids

def compare_video_ids(
        playlist_ids,
        metadata_ids
):
    """
    Tìm video có trong playlist
    nhưng không có metadata.
    """


    missing_metadata_ids = (
        playlist_ids - metadata_ids
    )


    print(
        f"Playlist video count: {len(playlist_ids)}"
    )


    print(
        f"Metadata video count: {len(metadata_ids)}"
    )


    print(
        f"Missing metadata videos: {len(missing_metadata_ids)}"
    )


    if missing_metadata_ids:

        print("Missing IDs:")

        for video_id in missing_metadata_ids:
            print(video_id)

def main():

    playlist_records = load_jsonl(
        PLAYLIST_FILE
    )


    metadata_records = load_jsonl(
        METADATA_FILE
    )


    playlist_ids = extract_playlist_video_ids(
        playlist_records
    )


    metadata_ids = extract_metadata_video_ids(
        metadata_records
    )


    compare_video_ids(
        playlist_ids,
        metadata_ids
    )



if __name__ == "__main__":
    main()