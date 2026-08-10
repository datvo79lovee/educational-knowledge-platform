# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-10

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
`Rewrite` cho q-038 và ba `Reject` cho q-024, q-028, q-036. q-042 đến q-044 giữ
Answer Points/evidence rỗng và chưa có quyết định canonical. Validation xác nhận
workbook reviewed chỉ thay đổi các cột review, không thay question, candidate
Answer Points, evidence hoặc Machine Data.

20 câu Batch 02 đạt review đã được canonicalize với `review_status=approved`,
reviewer `human_batch_02_2026-08-10`, expected Answer Points và exact evidence
range. Canonical dataset hiện có 33 record `approved`: 31 answerable và hai
out-of-scope. Không có duplicate question ID; mọi answerable record có Answer
Points, video ID và time range hợp lệ.

Coverage chưa hoàn tất. Batch 01 q-011 vẫn chưa canonical. Batch 02 còn bốn câu
`unresolved_no_primary` là q-015, q-020, q-025, q-032; ba câu bị Reject ở bước
Answer Points là q-024, q-028, q-036; q-042 đến q-044 là out-of-scope chưa có
quyết định canonical. Dataset còn thiếu ít nhất bảy record approved để đạt ngưỡng
tối thiểu 40 câu.

Chunking experiment đã có Gold contract, ba configuration và sample validation,
nhưng chưa đủ benchmark 40–60 câu để chạy retrieval comparison và chọn
configuration.

1. Review evidence hoặc rewrite riêng q-011, q-015, q-020, q-024, q-025, q-028,
   q-032 và q-036; không tự phục hồi câu đã Reject nếu chưa có evidence mới.
2. Quyết định có canonicalize q-042 đến q-044 làm out-of-scope controls hay không.
3. Mở rộng canonical dataset lên 40–60 record `approved`, đồng thời giữ Coverage
   Matrix đồng bộ.
4. Chạy retrieval comparison ba configuration bằng cùng question set `approved`,
   sau đó mới chọn configuration và build Gold 38 video.

Đã tạo Gold sample; chưa tạo Gold full corpus, embedding, vector index hoặc retrieval API.
