# PostgreSQL Loading Plan - Videos Table

## Mục tiêu

Load dữ liệu video đã được chuẩn hóa từ Silver Layer vào bảng `videos` trong PostgreSQL.

---

## Nguồn dữ liệu

Input file:

```text
data/silver/videos_clean.jsonl
```

Số lượng hiện tại:

```text
8021 records
```

Mỗi dòng là một JSON object.

Ví dụ:

```json
{
  "video_id": "oz1iDMr5INo",
  "source_id": 1,
  "title": "Could surveillance pricing work in consumers' favor?",
  "description": "...",
  "publish_date": "2026-06-16",
  "duration_seconds": 240,
  "view_count": 7437
}
```

---

## Bảng đích

```sql
videos
(
    video_id VARCHAR(50) PRIMARY KEY,
    source_id INT NOT NULL,

    title TEXT NOT NULL,
    description TEXT,

    publish_date DATE,

    duration_seconds INT,

    view_count BIGINT,

    ingested_at TIMESTAMP
)
```

---

## Mapping

| Silver Field     | PostgreSQL Column |
| ---------------- | ----------------- |
| video_id         | video_id          |
| source_id        | source_id         |
| title            | title             |
| description      | description       |
| publish_date     | publish_date      |
| duration_seconds | duration_seconds  |
| view_count       | view_count        |

Lưu ý:

* `ingested_at` sử dụng giá trị mặc định của PostgreSQL.
* Không cần truyền từ pipeline.

---

## Data Quality Assumptions

Đã xác nhận:

* 8021 records.
* Không có duplicate video_id.
* Không có missing title.
* Không có missing publish_date.
* Không có missing viewCount.
* Có 1 record có duration = P0D.

Quy tắc xử lý:

* P0D → duration_seconds = NULL.

---

## Loading Strategy

Bước 1:

Đọc file:

```text
data/silver/videos_clean.jsonl
```

Bước 2:

Parse từng record.

Bước 3:

Insert vào bảng:

```sql
videos
```

Bước 4:

Commit transaction.

---

## Duplicate Handling

Khóa chính:

```sql
video_id
```

Nếu video đã tồn tại:

```sql
ON CONFLICT (video_id)
DO NOTHING
```

Mục tiêu:

* Pipeline có thể chạy lại nhiều lần.
* Không tạo duplicate records.

---

## Validation Sau Khi Load

Kiểm tra số lượng:

```sql
SELECT COUNT(*)
FROM videos;
```

Kỳ vọng:

```text
8021
```

Kiểm tra duplicate:

```sql
SELECT video_id, COUNT(*)
FROM videos
GROUP BY video_id
HAVING COUNT(*) > 1;
```

Kỳ vọng:

```text
0 rows
```

---

## Deliverable Ngày 5

* Xây dựng file:

```text
src/loading/load_videos.py
```

* Load thành công Silver dataset vào PostgreSQL.
* Xác nhận số lượng records trong bảng videos.
