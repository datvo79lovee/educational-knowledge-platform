# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-11

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
- Silver transcript generated output:
  `data/silver/mit_60001/transcripts_clean.jsonl`
- Silver full validation:
  `reports/07_cleaning/full_validation.csv`
- Silver cleaning summary:
  `reports/07_cleaning/cleaning_summary.csv`
- Gold sample validation:
  `reports/08_chunking/sample_chunk_validation.csv`
- Gold sample cross-process validation:
  `reports/08_chunking/sample_chunk_cross_process_validation.csv`
- Gold sample generated output:
  `data/gold/mit_60001/samples/`
- Full-corpus chunk candidate validation:
  `reports/08_chunking/full_chunk_validation.csv`
- Full-corpus chunk candidate cross-process validation:
  `reports/08_chunking/full_chunk_cross_process_validation.csv`
- Dense retrieval comparison:
  `reports/08_chunking/chunking_comparison.csv`
- Dense retrieval detail:
  `reports/08_chunking/chunking_retrieval_results.csv`
- Chunking human review cuối cùng:
  `evaluation/review/chunking/mit_60001_chunking_citation_review_2026-08-11_reaudited.xlsx`
- Chunking configuration decision:
  `evaluation/review/chunking/mit_60001_chunking_configuration_decision_2026-08-12.csv`
- Canonical Gold full generated output:
  `data/gold/mit_60001/chunks.jsonl`
- Canonical Gold manifest:
  `reports/08_chunking/canonical_gold_manifest.json`
- Canonical Gold validation:
  `reports/08_chunking/canonical_gold_validation.csv`
- Canonical Gold cross-process validation:
  `reports/08_chunking/canonical_gold_cross_process_validation.csv`
- Canonical MIT 6.0001 evaluation dataset:
  `evaluation/mit_60001/evaluation_questions.jsonl`
- Current Batch 01 source candidates:
  `evaluation/review/batch_01/candidates/batch_01_source_candidates_with_transcript_2026-07-31_v2.csv`
- Batch 01 human decision workbook:
  `evaluation/review/batch_01/decisions/batch_01_review_vi_with_decision.xlsx`
- Batch 02 draft questions:
  `evaluation/drafts/mit_60001_question_drafts_batch_02.csv`
- Batch 02 candidate package:
  `evaluation/review/batch_02/candidates/batch_02_source_candidates_with_transcript_2026-08-01.csv`
- Batch 02 candidate decision record:
  `evaluation/review/batch_02/BATCH_02_CONTENT_REVIEW.md`
- Batch 02 candidate-level decision workbook:
  `evaluation/review/batch_02/decisions/batch_02_source_candidates_review_vi_translated.xlsx`
- Batch 02 evidence-role decision workbook:
  `evaluation/review/batch_02/decisions/batch_02_source_candidates_review_benchmark.xlsx`
- Batch 02 final evidence selection manifest:
  `evaluation/review/batch_02/decisions/batch_02_final_evidence_selection_2026-08-03.csv`
- Batch 02 candidate Answer Points workbook:
  `evaluation/review/batch_02/answer_points/batch_02_candidate_answer_points_review_2026-08-10.xlsx`
- Batch 02 reviewed Answer Points workbook:
  `evaluation/review/batch_02/answer_points/batch_02_candidate_answer_points_review_2026-08-10_reviewed.xlsx`
- Batch 02 completion review workbook:
  `evaluation/review/batch_02/completion/batch_02_completion_review_2026-08-11_reviewed.xlsx`
- MIT 6.0001 coverage matrix:
  `evaluation/coverage/MIT_60001_COVERAGE_MATRIX.md`

Không lưu `raw_text` đầy đủ trong folder `reports/`.

## Silver transcript cleaning

Silver v1 đã được build theo policy lossless `mit_60001_clean_v1`:

- Silver records: 38/38;
- unique video IDs: 38;
- playlist positions: 0–37;
- total segments: 12.518;
- record validation failures: 0;
- full output SHA-256:
  `50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb`.

Silver giữ nguyên từng segment text, timing, language và `is_generated` từ Bronze.
Nó bổ sung lineage, `content_sha256`, `cleaning_version` và transcript text dẫn xuất.
Full build được chạy lại ở Python process thứ hai và tạo byte giống nhau.

PostgreSQL vẫn không lưu segment timing, `is_generated`, segment count, content hash
hoặc cleaning version. Đây là chủ ý hiện tại: Silver JSONL là nguồn cho chunking và
citation, còn PostgreSQL giữ normalized transcript và JOIN metadata.

## Bước tiếp theo

### Evaluation canonical status

Batch 02 có 30 draft: 27 answerable và ba out-of-scope. Final evidence selection
đã chọn 23 Primary và 15 Supporting range cho 23 câu answerable. Candidate Answer
Points package gồm 22 record `candidate_ready`, một record
`blocked_evidence_not_entailing` là q-028 và ba record `out_of_scope`.

Human Answer Points review ngày 2026-08-10 có 19 quyết định `Accept`, một
`Rewrite` cho q-038 và ba `Reject` cho q-024, q-028, q-036. Completion review ngày
2026-08-11 xử lý bốn câu trước đó `unresolved_no_primary` và ba out-of-scope:
q-015, q-025, q-032, q-042, q-043 và q-044 được `Accept`; q-020 được `Rewrite`
để giới hạn intent vào `len`, indexing và slicing. Sáu evidence range của bốn câu
answerable đã được đối chiếu lại với Silver transcript.

27 câu Batch 02 đã được canonicalize với `review_status=approved`. Canonical dataset
hiện có 40 record `approved`: 35 answerable và năm out-of-scope; Batch 01 đóng góp
13 record, Batch 02 đóng góp 27 record. Không có duplicate question ID; mọi
answerable record có Answer Points, video ID và time range hợp lệ; mọi out-of-scope
record giữ Answer Points và evidence rỗng.

Benchmark đã đạt ngưỡng tối thiểu 40 câu trong mục tiêu 40–60. Các draft chưa
canonical còn q-011 của Batch 01 và ba câu Batch 02 bị human review `Reject` là
q-024, q-028, q-036. Không tự phục hồi các câu này nếu chưa có evidence hoặc quyết
định human review mới.

Chunking experiment đã build đủ ba full-corpus candidate cho 38 video và pass
schema, source coverage, timing/lineage, duplicate và cross-process determinism.
Dense retrieval comparison dùng 35 câu answerable và loại năm câu out-of-scope.

Human citation review cuối cùng dùng workbook reaudited. Kết quả theo configuration:

```text
fixed_wp240_o48_v1              : Correct 28, Incorrect 1, Good boundary 4, preferred 4
semantic_cosine_wp240_v1        : Correct 28, Incorrect 0, Good boundary 24, preferred 16
semantic_cosine_wp192_o32_v1    : Correct 25, Incorrect 0, Good boundary 20, preferred 14
Tie                             : 1
```

User đã approve `semantic_cosine_wp240_v1` ngày 2026-08-12. Raw deterministic
`chunking_comparison.csv` không bị sửa; decision CSV riêng là nguồn audit cho human
review và configuration được chọn.

Canonical Gold full đã được build byte-identical từ selected candidate:

```text
Output             : data/gold/mit_60001/chunks.jsonl
Configuration      : semantic_cosine_wp240_v1
Chunks             : 861
Videos             : 38/38
Silver coverage    : 12.518/12.518 segments
SHA-256            : c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432
Validation errors  : 0
Cross-process      : passed
```

Schema, lineage, source text/timing/hash, chunk ID/index, duplicate và coverage
validation đều pass. Canonical output, manifest và validation report byte-identical
qua hai Python processes.

1. Thiết kế và build embedding/index từ canonical Gold full.
2. Khóa embedding model revision, dimension, normalization, input/output hash và
   rebuild validation.
3. Sau khi index pass, triển khai Hybrid Search và Cross-Encoder evaluation.
4. q-011, q-024, q-028 và q-036 chỉ được mở lại khi có evidence hoặc quyết định
   human review mới; không chặn retrieval comparison hiện tại.

Canonical Gold full đã hoàn thành; chưa tạo embedding, vector index, Hybrid Search,
Cross-Encoder, LLM runtime hoặc retrieval API.
