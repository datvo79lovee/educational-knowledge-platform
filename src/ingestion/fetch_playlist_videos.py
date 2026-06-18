from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
import json

load_dotenv()

youtube = build(
    "youtube",
    "v3",
    developerKey=os.getenv("YOUTUBE_API_KEY")
)

UPLOADS_PLAYLIST_ID = "UUEBb1b_L6zDS3xTUrIALZOw"

all_items = []

next_page_token = None

while True:

    response = youtube.playlistItems().list(
        part="snippet",
        playlistId=UPLOADS_PLAYLIST_ID,
        maxResults=50,
        pageToken=next_page_token
    ).execute()

    items = response["items"]

    all_items.extend(items)

    print(f"Fetched {len(items)} videos")

    next_page_token = response.get("nextPageToken")

    if next_page_token is None:
        break

print(f"\nTotal videos: {len(all_items)}")
with open(
    "data/bronze/videos_raw.jsonl",
    "w",
    encoding="utf-8"
) as f:

    for item in all_items:
        f.write(
            json.dumps(item, ensure_ascii=False)
        )
        f.write("\n")

print("Bronze file saved.")