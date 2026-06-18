from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
load_dotenv()
youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

response = youtube.search().list(
    q = "MIT OpenCourseWare",
    part = "snippet",
    type ="channel",
    maxResults = 1
).execute()

print(response)