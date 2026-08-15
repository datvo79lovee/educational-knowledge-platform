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

Trạng thái: hoàn thành ngày 2026-08-12.

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

### Output hiện có

```text
docs/design/GOLD_CHUNK_CONTRACT.md
docs/design/CHUNKING_EXPERIMENT.md
docs/design/CHUNKING_EVALUATION_CONTRACT.md
schemas/gold_chunk_v1.schema.json
schemas/chunking_evaluation_question_v1.schema.json
scripts/chunking/build_chunk_samples.py
reports/08_chunking/sample_chunk_validation.csv
reports/08_chunking/sample_chunk_cross_process_validation.csv
reports/08_chunking/full_chunk_validation.csv
reports/08_chunking/full_chunk_cross_process_validation.csv
reports/08_chunking/chunking_retrieval_results.csv
reports/08_chunking/chunking_comparison.csv
reports/08_chunking/retrieval_run_manifest.json
reports/08_chunking/retrieval_cross_process_validation.csv
evaluation/review/chunking/mit_60001_chunking_citation_review_2026-08-11_reaudited.xlsx
evaluation/review/chunking/mit_60001_chunking_configuration_decision_2026-08-12.csv
scripts/chunking/promote_selected_config.py
scripts/chunking/verify_canonical_gold_cross_process.py
reports/08_chunking/canonical_gold_manifest.json
reports/08_chunking/canonical_gold_validation.csv
reports/08_chunking/canonical_gold_cross_process_validation.csv
```

Sample năm video và full corpus 38 video đã pass schema, source coverage,
timing/lineage validation và cross-process determinism cho cả ba configuration.
Dense retrieval dùng cùng 35 câu `approved`, `answerable=true`; năm câu
out-of-scope không tham gia Recall/MRR.

Human citation review và re-audit đã hoàn tất cho 35 câu. User approve
`semantic_cosine_wp240_v1` ngày 2026-08-12. Decision artifact khóa retrieval run,
review workbook hash, human counts và automatic metrics.

Canonical `data/gold/mit_60001/chunks.jsonl` đã được promote byte-identical từ
selected candidate: 861 chunks, 38 video, đủ 12.518 Silver segments. Schema,
lineage, text/timing/hash, chunk ID/index, coverage và cross-process determinism đều
pass. Canonical JSONL là generated data bị gitignore; manifest và validation reports
được commit.

### Canonical generated output

```text
data/gold/mit_60001/chunks.jsonl
```

## Phase 6 — Embedding và vector index

Trạng thái: hoàn thành ngày 2026-08-12.

### Quyết định đã triển khai

- Model `sentence-transformers/all-MiniLM-L6-v2`, revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Exact local index `numpy_exact_cosine_v1`, float32, 384 chiều và L2-normalized.
- Index chỉ chứa 861 canonical Gold chunks của 38 MIT 6.0001 video.
- Generated vectors/metadata nằm tại `data/indexes/mit_60001/` và bị gitignore.
- Manifest khóa model/runtime, thời điểm build, canonical input hash, thứ tự chunk ID,
  embeddings hash, metadata hash và combined index content hash.
- Builder hỗ trợ rebuild trực tiếp từ canonical Gold và dừng khi scope, count, hash,
  model revision, dimension hoặc vector invariants không đúng.

### Output hiện có

```text
scripts/embedding/build_mit_60001_index.py
scripts/embedding/verify_index_cross_process.py
scripts/embedding/evaluate_index_retrieval.py
scripts/embedding/verify_index_retrieval_cross_process.py
schemas/embedding_index_manifest_v1.schema.json
reports/09_embedding/embedding_index_manifest.json
reports/09_embedding/embedding_index_validation.csv
reports/09_embedding/embedding_index_cross_process_validation.csv
reports/09_embedding/production_index_retrieval_results.csv
reports/09_embedding/production_index_retrieval_comparison.csv
reports/09_embedding/production_index_retrieval_manifest.json
reports/09_embedding/production_index_retrieval_cross_process_validation.csv
```

Index build pass với 861 unique chunk IDs, 38 video, shape `861 x 384`, không có
NaN/Infinity, zero-norm hoặc norm violation. Bốn index artifact byte-identical qua
hai Python processes.

Production-index retrieval dùng 35 answerable questions và 57 Ground Truth ranges.
Toàn bộ metrics và Top 10 IDs/scores của 35/35 câu khớp dense baseline đã khóa.
Ba retrieval artifact byte-identical qua hai Python processes.

## Phase 7 — Retrieval, reranking và Search API

Trạng thái: lexical/Hybrid comparison, Cross-Encoder evaluation và human configuration
decision hoàn thành ngày 2026-08-15; Search API chưa triển khai.

### Retrieval experiment đã hoàn thành

- Exact BM25 index gồm 861 documents, 3.334 vocabulary terms và 57.804 posting entries.
- Đã so sánh `dense_baseline_v1`, `bm25_v1` và `hybrid_rrf_k60_d100_v1` trên cùng
  35 answerable questions và 57 Ground Truth ranges.
- Dense branch khớp locked production baseline ở toàn bộ metrics, Top 10 IDs 35/35
  và Top 10 scores 35/35.
- Lexical index và retrieval reports đều byte-identical qua hai Python processes.
- User chọn `dense_baseline_v1` ngày 2026-08-14. BM25 và equal-weight RRF là
  evaluated non-selected baselines.

### Output hiện có

```text
scripts/retrieval/build_mit_60001_lexical_index.py
scripts/retrieval/evaluate_hybrid_retrieval.py
scripts/retrieval/verify_lexical_index_cross_process.py
scripts/retrieval/verify_hybrid_retrieval_cross_process.py
schemas/lexical_index_manifest_v1.schema.json
reports/10_retrieval/lexical_index_manifest.json
reports/10_retrieval/lexical_index_validation.csv
reports/10_retrieval/lexical_index_cross_process_validation.csv
reports/10_retrieval/hybrid_retrieval_results.csv
reports/10_retrieval/hybrid_retrieval_comparison.csv
reports/10_retrieval/hybrid_retrieval_question_comparison.csv
reports/10_retrieval/hybrid_retrieval_manifest.json
reports/10_retrieval/hybrid_retrieval_cross_process_validation.csv
reports/10_retrieval/retrieval_configuration_decision_2026-08-14.csv
```

Raw comparison giữ `pending_human_decision`; decision CSV riêng là nguồn selection
sau human review và khóa hash của comparison, question package, cross-process report.

### Cross-Encoder experiment đã hoàn thành

- Dense Top 50 chứa first relevant và đầy đủ Ground Truth evidence cho 35/35 câu.
- Đã rerank 1.750 question–chunk pairs bằng
  `cross-encoder/ms-marco-MiniLM-L6-v2`, revision
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`.
- Cross-Encoder có MRR 0,532611871, thấp hơn Dense 0,573585434; Recall@1/3/5 cũng
  thấp hơn, Recall@10 bằng 0,914285714.
- Năm report artifact byte-identical với verification process độc lập.
- Human review 35/35 câu: Dense 15, Cross-Encoder 13, Tie 7.
- User giữ `dense_baseline_v1` ngày 2026-08-15. Cross-Encoder là evaluated
  non-selected reranker và không nằm trong MVP runtime path.

Output bổ sung:

```text
scripts/retrieval/evaluate_cross_encoder_reranking.py
scripts/retrieval/verify_cross_encoder_reranking_cross_process.py
schemas/cross_encoder_reranking_manifest_v1.schema.json
reports/11_reranking/cross_encoder_reranking_results.csv
reports/11_reranking/cross_encoder_reranking_comparison.csv
reports/11_reranking/cross_encoder_reranking_question_comparison.csv
reports/11_reranking/cross_encoder_reranking_validation.csv
reports/11_reranking/cross_encoder_reranking_manifest.json
reports/11_reranking/cross_encoder_reranking_cross_process_validation.csv
reports/11_reranking/reranking_configuration_decision_2026-08-15.csv
evaluation/review/reranking/cross_encoder_reranking_review_2026-08-15_reviewed.xlsx
```

### Việc cần làm trước API

- Xây API bằng selected Dense baseline; output retrieval cho MVP là Dense Top 3.
- Khóa request/response schema, ranking tie-break và validation cho API.
- Khóa chính sách accept/reject trước grounded answer generation.

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

Trạng thái: canonical question set và dense retrieval metrics đã hoàn thành; chưa
đánh giá answer groundedness hoặc abstention accuracy end-to-end.

### Bộ câu hỏi

Canonical dataset hiện có 40 câu `approved`: 35 answerable và năm out-of-scope.
Batch 01 đóng góp 13 record, Batch 02 đóng góp 27 record. Bộ câu hỏi phủ các nhóm:

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
7. Chunking experiment (hoàn thành)
8. Embedding/index (hoàn thành)
9. Lexical/Hybrid comparison và retrieval selection (hoàn thành)
10. Cross-Encoder evaluation (hoàn thành; không được chọn)
11. Retrieval/Search API (bước kế tiếp)
12. Grounded answer evaluation
```

## Việc chưa làm

- Chưa thay đổi PostgreSQL schema để lưu vector; MVP đang dùng exact local index.
- Cross-Encoder đã đánh giá nhưng không được tích hợp vào MVP runtime path.
- Chưa xây LLM accept/reject runtime, grounded answer generation hoặc Search API.
- Chưa đánh giá answer groundedness và abstention accuracy end-to-end.
