# Chunking experiment v1

## Trạng thái

Đã chốt design ngày 2026-07-27. Chưa cài encoder, chưa tạo Gold chunk và chưa chọn
cấu hình thắng cuộc.

## Mục tiêu

So sánh fixed-token baseline với semantic chunking trên cùng Silver v1 và cùng
evaluation set. Mọi configuration phải tuân theo `GOLD_CHUNK_CONTRACT.md`.

```text
scope_version: mit_60001_fall_2016_v1
silver_content: data/silver/mit_60001/transcripts_clean.jsonl
chunking_version: mit_60001_chunk_v1
tokenizer: tokenizer của encoder đã pin revision
token unit: word piece token
```

Token count dùng tokenizer của semantic encoder, không dùng số từ hoặc số ký tự làm
thay thế. Mọi chunk chỉ lấy whole Silver segment; không cắt giữa segment để đạt một
con số token chính xác.

## Tiền xử lý hợp lệ

`segments[].text` và `chunk_text` luôn giữ nguyên text Silver. Để tạo embedding
semantic window, chunker được phép dùng derived view chỉ cho encoder: thay newline
bằng space và collapse whitespace. Derived view không được ghi vào Gold, không được
dùng để so sánh text lineage và không được dùng lại làm `chunk_text`.

## Semantic boundary algorithm

1. Gom các segment liên tiếp thành semantic window khoảng 32–64 word pieces.
2. Encode từng window bằng encoder đã pin revision và L2-normalize vector.
3. Tại mỗi ranh giới giữa hai window, tính cosine similarity giữa hai vector kề nhau.
4. Khi chunk hiện tại đạt minimum size, ưu tiên boundary có similarity thấp nhất
   trong vùng tìm kiếm trước hard maximum.
5. Hard maximum luôn thắng semantic score; chunk không vượt maximum.
6. Nếu không có candidate hợp lệ, đóng chunk tại whole segment cuối cùng còn nằm
   trong hard maximum.

Không gọi LLM để viết lại câu, tóm tắt hoặc phỏng đoán topic. Semantic algorithm chỉ
chọn ranh giới giữa các segment đã tồn tại.

## Ba configuration phải so sánh

| Config ID | Strategy | Min / preferred / max word pieces | Overlap | Mục đích |
| --- | --- | --- | --- | --- |
| `fixed_wp240_o48_v1` | Greedy fixed-token baseline | 192 / 240 / 240 | mục tiêu 48, whole segment | Baseline không semantic score |
| `semantic_cosine_wp240_v1` | Lowest adjacent-window cosine boundary | 96 / 192 / 240 | 0 | Semantic boundary không lặp context |
| `semantic_cosine_wp192_o32_v1` | Lowest adjacent-window cosine boundary | 72 / 160 / 192 | mục tiêu 32, whole segment | Chunk nhỏ hơn, overlap nhẹ |

Overlap là mục tiêu gần đúng vì không được cắt segment. Builder phải ghi actual overlap
distribution vào report thay vì tuyên bố mọi chunk có đúng số token overlap.

Nếu một segment đơn lẻ vượt hard maximum, builder giữ nguyên segment trong một chunk,
ghi `oversize_single_segment_count` vào report và không cắt text.

Minimum là target, không phải lý do để cắt segment. Nếu tail chunk nhỏ hơn minimum,
builder thử merge vào chunk trước khi không vượt hard maximum; nếu merge vượt maximum,
giữ tail chunk nhỏ và ghi `undersize_tail_chunk_count` vào report. First chunk, tail
chunk và oversize-single-segment chunk được miễn minimum; mọi chunk khác phải đạt
minimum hoặc run validation thất bại.

## Điều kiện so sánh công bằng

- Mọi configuration đọc đúng Silver file và scope version như nhau.
- Mỗi configuration có Gold JSONL, validation report và run metadata riêng.
- Không trộn chunk của configuration khác khi retrieval evaluation.
- Cùng câu hỏi, relevance labels, embedding retrieval setup và `k` được dùng cho cả ba.
- Không chọn configuration theo số chunk ít/nhiều hoặc theo cảm nhận; quyết định dựa
  trên retrieval metrics và manual citation review ở Milestone 4.

## Report tối thiểu cho mỗi run

```text
chunking_config_id
encoder_repository
encoder_revision
sentence_transformers_version
tokenizer_revision
tokenizer_name
total_chunks
chunks_per_video_min/max/mean
token_count_min/max/mean
actual_overlap_token_min/max/mean
oversize_single_segment_count
undersize_tail_chunk_count
undersize_non_tail_chunk_count
oversize_multi_segment_chunk_count
source_segment_coverage
duplicate_chunk_id_count
validation_status
output_sha256
```

Report không chứa `chunk_text`, Silver transcript text hoặc embedding vector.

Sample phải có thêm `sample_chunk_cross_process_validation.csv`, xác minh SHA-256
của từng configuration giống nhau sau hai Python process độc lập.

## Điều kiện chuyển sang implementation sample

Trước khi Milestone 5 chạy, phải có Gold contract hợp lệ, ba configuration nêu trên
và evaluation contract/template. Sample chỉ dùng năm video đã chọn ở Silver validation.
