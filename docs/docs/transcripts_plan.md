# Transcript Ingestion Plan

## Objective

Thu thập transcript từ YouTube cho các video đã được lưu trong bảng videos.

Transcript sẽ được sử dụng cho:

- Knowledge Processing
- Chunk Generation
- Embedding Generation
- Semantic Search

Mục tiêu của pipeline:

- Thu transcript từ YouTube
- Lưu transcript vào Bronze Layer
- Kiểm tra chất lượng dữ liệu
- Chuẩn bị cho Chunking Pipeline
---
## Data Flow

videos table
        ↓
fetch_transcripts.py
        ↓
transcripts_raw.jsonl
        ↓
Transcript Quality Check
        ↓
transcripts_clean.jsonl
        ↓
load_transcripts.py
        ↓
transcripts table
        ↓
chunking pipeline
---
## Data Source

Library:

youtube-transcript-api

Input:

videos.video_id

Output:

Transcript segments:

[
    {
        "text": "...",
        "start": 0.0,
        "duration": 4.5
    }
]
---
## Bronze Transcript Schema

File:

data/bronze/transcripts_raw.jsonl

Example:

{
    "video_id": "abc123",

    "language": "en",

    "segments": [
        {
            "text": "Hello everyone",
            "start": 0.0,
            "duration": 2.1
        },
        {
            "text": "Welcome to MIT",
            "start": 2.1,
            "duration": 3.4
        }
    ]
}
---

---

## Phần 5. Silver Schema

```md
## Silver Transcript Schema

File:

data/silver/transcripts_clean.jsonl

Example:

{
    "video_id": "abc123",

    "language": "en",

    "raw_text": "Hello everyone Welcome to MIT ..."
}
---

---

## Phần 6. Transcript Status

```md
## Transcript Status

available

not_found

disabled

private

error