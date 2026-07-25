# Trạng thái hiện tại

## Ngày ghi nhận

2026-07-25

## Corpus mục tiêu

```text
Course: MIT 6.0001
Title: Introduction to Computer Science and Programming in Python
Term: Fall 2016
Playlist ID: PLUl4u3cNGP63WbdFxL8giv4yhgdMGaZNA
Scope version: mit_60001_fall_2016_v1
Target videos: 38
```

286 transcript ngoài target playlist không bị xóa. Chúng không được đưa vào
cleaning, chunking, embedding hoặc evaluation của MVP MIT 6.0001.

## Số lượng dữ liệu

- Nguồn trong PostgreSQL: 1
- Video trong PostgreSQL: 8.021
- Transcript thành công trong Bronze JSONL: 324
- Video ID duy nhất trong Bronze transcript: 324
- Transcript trong PostgreSQL: 324
- Target transcript trong Bronze: 38/38
- Target transcript trong PostgreSQL: 38/38
- Tổng số dòng checkpoint: 338
- Số video duy nhất xuất hiện trong checkpoint: 336

Trạng thái checkpoint mới nhất:

| Trạng thái | Số video |
| --- | ---: |
| `success` | 324 |
| `no_transcript` | 5 |
| `transcripts_disabled` | 5 |
| `fetch_failed` | 1 |
| `ip_blocked` | 1 |

Checkpoint là append-only nên 338 dòng lịch sử đại diện cho 336 video duy nhất.

## Target acquisition

- Payload có sẵn trước targeted acquisition: 4
- Payload mới thu thập: 34
- Target payload hiện tại: 38/38
- Target `not_attempted`: 0
- Target permanently unavailable: 0
- Target retryable failure: 0
- Target cần manual review: 0

Target manifest v1 được giữ bất biến. Nếu playlist thay đổi phải tạo scope version
mới thay vì ghi đè manifest hiện tại.

## PostgreSQL load và validation

Loader đã chèn 34 transcript mới:

```text
Before count : 290
Inserted     : 34
After count  : 324
```

Kết quả validation read-only:

| Chỉ số | Kết quả |
| --- | ---: |
| Target JOIN rows | 38 |
| Target video ID duy nhất | 38 |
| Thiếu metadata video | 0 |
| Thiếu target transcript | 0 |
| Target transcript bị trùng | 0 |
| `raw_text` rỗng | 0 |
| `language` rỗng | 0 |
| Transcript length nhỏ nhất | 653 |
| Transcript length lớn nhất | 49.645 |
| Transcript length trung bình | 13.243 |

Validation status: `passed`.

## Source of truth

- Target scope: `reports/04_scope_decision/target_manifest.csv`
- Bronze payload: `data/bronze/transcripts_raw.jsonl`
- Checkpoint: `data/bronze/transcripts_checkpoint.jsonl`
- PostgreSQL normalized transcript: bảng `transcripts`
- Target acquisition status:
  `reports/05_target_corpus/acquisition_status.csv`
- PostgreSQL validation:
  `reports/06_transcript_load_validation/validation_summary.csv`
- Target transcript detail:
  `reports/06_transcript_load_validation/target_transcript_validation.csv`

Không lưu `raw_text` đầy đủ trong folder `reports/`.

## Vấn đề chưa xử lý

Schema PostgreSQL hiện chưa lưu:

- segment timing;
- `is_generated`;
- segment count;
- content hash;
- cleaning version.

Các field này vẫn còn trong Bronze payload khi nguồn cung cấp có dữ liệu tương ứng.
Phải quyết định Silver transcript contract trước khi cleaning và chunking.

## Bước tiếp theo

Thiết kế Silver transcript schema cho đúng 38 target videos:

1. Xác định field và kiểu dữ liệu bắt buộc.
2. Giữ lineage tới Bronze payload và target manifest.
3. Giữ segment timing để citation có thể mở đúng thời điểm video.
4. Định nghĩa normalization an toàn cho text và code.
5. Tạo `content_hash` và `cleaning_version`.
6. Test trên một sample nhỏ trước khi xử lý đủ corpus.

Chưa tạo chunk, embedding hoặc vector index trong bước hiện tại.
