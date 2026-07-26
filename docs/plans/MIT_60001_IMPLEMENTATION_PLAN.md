# Kế hoạch triển khai corpus MIT 6.0001

## Mục tiêu

Xây dựng semantic search và grounded question answering trên MIT 6.0001 Fall 2016,
có citation tới video và khoảng thời gian, có khả năng từ chối câu hỏi ngoài corpus
và có bộ đánh giá do người có kiến thức Python kiểm tra.

## Nguyên tắc

- Không crawl lại toàn bộ channel.
- Không xóa 286 transcript ngoài scope.
- Không coi playlist item nào cũng chắc chắn có transcript.
- Không chunk hoặc embedding dữ liệu ngoài target manifest.
- Mọi output phải có version và có thể tái tạo.
- Retrieval phải trả nguồn; không đánh giá chỉ bằng độ trôi chảy của câu trả lời.

## Phase 1 — Target inventory và gap report

Trạng thái: hoàn thành ngày 2026-07-13.

### Việc cần làm

1. Thu đầy đủ 38 playlist items gồm position, video ID và title.
2. Đối chiếu với PostgreSQL, Bronze transcript và checkpoint.
3. Phân loại từng video:

```text
already_available
not_attempted
no_transcript
transcripts_disabled
retryable_failure
```

4. Tạo target manifest bất biến cho lần triển khai đầu tiên.

### Output

```text
reports/04_scope_decision/target_playlist_inventory.csv
reports/04_scope_decision/target_gap_report.csv
reports/04_scope_decision/target_manifest.csv
```

### Điều kiện hoàn thành

- Có đúng 38 video ID duy nhất.
- Xác nhận 4 transcript hiện có.
- Có danh sách chính xác video cần fetch.

## Phase 2 — Targeted transcript acquisition

Trạng thái: hoàn thành ngày 2026-07-23.

### Việc cần làm

1. Chỉ đưa video `not_attempted` hoặc lỗi retryable vào queue.
2. Tái sử dụng delay, checkpoint, resume và stop-on-block hiện có.
3. Ghi payload thành công vào Bronze transcript source of truth.
4. Không ghi payload giả cho video không có transcript.
5. Reconcile Bronze payload với checkpoint sau mỗi phiên chạy.

### Output

```text
reports/05_target_corpus/acquisition_status.csv
reports/05_target_corpus/acquisition_summary.csv
```

### Điều kiện hoàn thành

- Mọi video trong manifest có trạng thái cuối hoặc retryable rõ ràng.
- Không có duplicate payload theo video ID.
- Không fetch video ngoài playlist mục tiêu.

### Kết quả

```text
Target payloads: 38/38
Payload mới: 34
Not attempted: 0
Permanently unavailable: 0
Retryable failures: 0
```

## Phase 3 — PostgreSQL reconciliation

Trạng thái: hoàn thành ngày 2026-07-25.

### Việc cần làm

1. Load transcript thành công mới vào PostgreSQL bằng transaction.
2. Kiểm tra foreign key với `videos`.
3. Không tạo transcript trùng khi chạy lại.
4. Xuất báo cáo JOIN riêng cho target corpus.

### Output

```text
scripts/transcript_loading/validate_target_postgresql.py
reports/06_transcript_load_validation/validation_summary.csv
reports/06_transcript_load_validation/target_transcript_validation.csv
docs/reports/06_transcript_load_validation/POSTGRESQL_TARGET_LOAD_REPORT.md
```

### Kết quả

```text
PostgreSQL transcripts: 324
Target JOIN coverage: 38/38
Missing target transcripts: 0
Duplicate target transcripts: 0
Empty raw_text: 0
Empty language: 0
Validation status: passed
```

### Quyết định schema cần xử lý

Schema hiện tại chưa giữ `is_generated`, segment count, content hash và segment
timing. Trước khi chunking phải quyết định:

- ALTER TABLE để lưu metadata cần thiết; hoặc
- giữ PostgreSQL cho normalized transcript và dùng Silver JSONL làm nguồn segment
  timing.

Không drop table. Migration phải tương thích dữ liệu 324 transcript hiện có.

## Phase 4 — Transcript cleaning

Trạng thái: hoàn thành ngày 2026-07-26.

### Cách triển khai

- Giữ nguyên Bronze payload.
- Áp dụng `mit_60001_clean_v1`: lossless, không chuẩn hóa whitespace, không xóa
  segment và không sửa transcript.
- Không tự sửa code, toán tử hoặc indentation bằng phỏng đoán.
- Giữ `start`, `duration`, language và `is_generated`.
- Tạo `content_hash` và `cleaning_version`.
- Dùng một shared builder cho sample và full build; kiểm tra rebuild trong process
  và chạy full build lại ở process khác để so sánh SHA-256.

### Output

```text
data/silver/mit_60001/transcripts_clean.jsonl
scripts/cleaning/silver_builder.py
scripts/cleaning/build_silver_full.py
reports/07_cleaning/full_validation.csv
reports/07_cleaning/cleaning_summary.csv
docs/reports/07_cleaning/SILVER_FULL_BUILD_REPORT.md
```

### Kết quả

```text
Silver records: 38/38
Unique video IDs: 38
Playlist positions: 0..37
Segments: 12,518
Failed record validations: 0
Full output SHA-256: 50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb
Cross-process byte comparison: passed
```

## Phase 5 — Chunking experiment

Không chọn kích thước chunk chỉ theo cảm tính. Cần thử ít nhất ba cấu hình trên cùng
một tập câu hỏi và so sánh retrieval.

Mỗi chunk phải có:

```text
chunk_id
video_id
playlist_position
chunk_index
chunk_text
start_second
end_second
chunking_version
content_hash
```

Các cấu hình cần thay đổi kích thước và overlap nhưng phải giữ ranh giới thời gian
đủ chính xác để citation mở đúng đoạn video.

### Output dự kiến

```text
data/gold/mit_60001/chunks.jsonl
reports/08_chunking/chunking_comparison.csv
```

## Phase 6 — Embedding và vector index

### Việc cần làm

- Chọn embedding model có version cố định.
- Lưu model name, dimension và thời điểm tạo index.
- Tạo collection/index riêng cho MIT 6.0001.
- Hỗ trợ rebuild từ Gold chunks.
- Không trộn 286 transcript ngoài scope vào index MVP.

## Phase 7 — Retrieval và Search API

API tối thiểu:

```text
POST /search
GET /videos/{video_id}
```

Mỗi search result phải trả:

```text
chunk_text
score
video_id
video_title
start_second
end_second
source_url
```

Nếu có answer generation, câu trả lời phải:

- chỉ sử dụng retrieved context;
- có citation tới video/timestamp;
- nói không đủ dữ liệu khi context không hỗ trợ;
- không trả lời như trợ lý Python tổng quát.

## Phase 8 — Evaluation chống hallucination

### Bộ câu hỏi

Tạo khoảng 40–60 câu hỏi gồm:

- factual retrieval;
- giải thích khái niệm;
- hành vi của đoạn code;
- câu hỏi cần kết hợp nhiều chunk;
- câu hỏi dễ nhầm giữa hai bài;
- câu hỏi ngoài phạm vi.

Mỗi câu hỏi cần:

```text
question_id
question
expected_answer_points
relevant_video_ids
relevant_time_ranges
answerable
review_notes
```

### Chỉ số

- Recall@k cho relevant chunks.
- MRR hoặc rank của chunk đầu tiên đúng.
- Citation correctness.
- Answer groundedness bằng manual review.
- Abstention accuracy cho câu hỏi ngoài scope.

Không dùng một LLM khác làm nguồn đánh giá duy nhất.

## Phase 9 — Demo và tài liệu

- README mô tả đúng phạm vi MIT 6.0001.
- Data flow và schema được cập nhật.
- Có lệnh rebuild corpus/index từ đầu.
- Có ví dụ search đúng, search thất bại và câu hỏi ngoài scope.
- Không tuyên bố hệ thống hiểu Python nói chung.

## Thứ tự thực hiện ngay

```text
1. Target inventory
2. Gap report
3. Targeted transcript fetch
4. Reconcile và load PostgreSQL
5. Schema/segment decision
6. Cleaning (hoàn thành)
7. Chunking experiment (bước kế tiếp)
8. Embedding/index
9. Retrieval API
10. Evaluation
```

## Việc chưa làm

- Chưa thay đổi schema.
- Chưa chunking hoặc embedding.
- Chưa chọn embedding model hoặc vector database.
