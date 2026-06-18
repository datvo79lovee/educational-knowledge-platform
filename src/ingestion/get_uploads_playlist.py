from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
""""Hỏi YouTube: "Playlist nào chứa toàn bộ video upload của channel này?"
-> Nhận được Uploads Playlist ID
mục đích: tìm Uploads Playlist ID"""

load_dotenv()

youtube = build(
    "youtube",
    "v3",
    developerKey=os.getenv("YOUTUBE_API_KEY")
)

CHANNEL_ID = "UCEBb1b_L6zDS3xTUrIALZOw"

response = youtube.channels().list(
    part="contentDetails",
    id=CHANNEL_ID
).execute()

print(response)
print()
print(response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"])