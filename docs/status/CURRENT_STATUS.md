# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-20

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
- MIT 6.0001 embedding index generated output:
  `data/indexes/mit_60001/`
- Embedding index manifest:
  `reports/09_embedding/embedding_index_manifest.json`
- Embedding index validation:
  `reports/09_embedding/embedding_index_validation.csv`
- Embedding index cross-process validation:
  `reports/09_embedding/embedding_index_cross_process_validation.csv`
- Production-index retrieval comparison:
  `reports/09_embedding/production_index_retrieval_comparison.csv`
- Production-index retrieval cross-process validation:
  `reports/09_embedding/production_index_retrieval_cross_process_validation.csv`
- Lexical index manifest và validation:
  `reports/10_retrieval/lexical_index_manifest.json`
  và `reports/10_retrieval/lexical_index_validation.csv`
- Dense/BM25/RRF comparison:
  `reports/10_retrieval/hybrid_retrieval_comparison.csv`
- Retrieval comparison theo từng câu:
  `reports/10_retrieval/hybrid_retrieval_question_comparison.csv`
- Retrieval configuration decision:
  `reports/10_retrieval/retrieval_configuration_decision_2026-08-14.csv`
- Cross-Encoder reranking manifest và comparison:
  `reports/11_reranking/cross_encoder_reranking_manifest.json`
  và `reports/11_reranking/cross_encoder_reranking_comparison.csv`
- Cross-Encoder cross-process validation:
  `reports/11_reranking/cross_encoder_reranking_cross_process_validation.csv`
- Cross-Encoder human review workbook:
  `evaluation/review/reranking/cross_encoder_reranking_review_2026-08-15_reviewed.xlsx`
- Reranking configuration decision:
  `reports/11_reranking/reranking_configuration_decision_2026-08-15.csv`
- Search API contract và runtime schema:
  `docs/design/SEARCH_API_CONTRACT.md`
  và `schemas/search_api_v1.schema.json`
- Search API validation manifest:
  `reports/12_search_api/search_api_validation_manifest.json`
- Search API cross-process validation:
  `reports/12_search_api/search_api_cross_process_validation.csv`
- Evidence review request package và manifest:
  `evaluation/review/evidence_accept_reject/evidence_review_requests_v1.jsonl`
  và `reports/phase_08_evidence_reviewer/13_evidence_review/evidence_review_package_manifest.json`
- Evidence reviewer runtime manifest:
  `reports/phase_08_evidence_reviewer/14_evidence_review_runtime/evidence_review_runtime_manifest.json`
- Baseline evidence reviewer evaluation:
  `reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/final_metrics.json`
  và `reports/phase_08_evidence_reviewer/15_evidence_reviewer_evaluation/evidence_reviewer_evaluation_manifest.json`
- Prompt V2 experiment manifest:
  `reports/phase_08_evidence_reviewer/16_evidence_reviewer_prompt_experiment/prompt_experiment_manifest.json`
- Prompt V2 final evaluation và human evidence audit:
  `reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/final_metrics.json`
  và `reports/phase_08_evidence_reviewer/17_evidence_reviewer_prompt_evaluation/m3_final_manifest.json`
- A1 two-stage reviewer runtime và stability manifest:
  `reports/phase_08_evidence_reviewer/18_evidence_reviewer_a1_experiment/a1_experiment_manifest.json`
  và `reports/phase_08_evidence_reviewer/18_evidence_reviewer_a1_experiment/a1_stability_comparison.json`
- A1 canonical evaluation và final decision manifest:
  `reports/phase_08_evidence_reviewer/19_evidence_reviewer_a1_evaluation/a1_final_metrics.json`
  và `reports/phase_08_evidence_reviewer/19_evidence_reviewer_a1_evaluation/a1_m3_final_manifest.json`
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

Embedding/index Phase 6 đã hoàn thành từ canonical Gold full:

```text
Index run ID       : mit60001_index_558e4d6e873847dd
Backend            : numpy_exact_cosine_v1
Model              : sentence-transformers/all-MiniLM-L6-v2
Model revision     : 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
Chunks / videos    : 861 / 38
Embedding shape    : 861 x 384
Embedding dtype    : float32
Normalization      : L2
Index content hash : 6e78f39257b7cc5defebd6740aab2dc1a4c202165b073f7a740ee5a5d7c46805
Validation errors  : 0
Cross-process      : passed
```

Production-index retrieval dùng đúng 35 canonical answerable questions và 57 Ground
Truth ranges. Kết quả khớp dense baseline của selected configuration ở toàn bộ metrics,
Top 10 chunk IDs 35/35 và Top 10 scores 35/35:

| Metric | Kết quả |
| --- | ---: |
| MRR | 0,573585434 |
| Recall@1 | 0,371428571 |
| Recall@3 | 0,742857143 |
| Recall@5 | 0,857142857 |
| Recall@10 | 0,914285714 |

Retrieval detail, comparison và run manifest byte-identical qua hai Python processes.

Exact BM25 index và equal-weight RRF experiment đã hoàn thành. Lexical index có 861
documents, 3.334 vocabulary terms, 57.804 posting entries và validation errors bằng 0.
Lexical index cùng bốn Hybrid retrieval reports byte-identical qua hai Python processes.

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `bm25_v1` | 0,443842416 | 0,257142857 | 0,600000000 | 0,628571429 | 0,714285714 |
| `hybrid_rrf_k60_d100_v1` | 0,517862148 | 0,342857143 | 0,571428571 | 0,828571429 | 0,914285714 |

User chọn `dense_baseline_v1` ngày 2026-08-14. `bm25_v1` và
`hybrid_rrf_k60_d100_v1` không được chọn. Raw deterministic comparison không bị sửa;
decision CSV riêng khóa human selection và các input artifact hashes.

Cross-Encoder experiment đã rerank Dense Top 50 bằng
`cross-encoder/ms-marco-MiniLM-L6-v2`, revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`, rồi so sánh trên cùng 35 answerable
questions và 57 Ground Truth ranges:

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `cross_encoder_ms_marco_minilm_l6_v2` | 0,532611871 | 0,342857143 | 0,657142857 | 0,771428571 | 0,914285714 |

Năm report artifact byte-identical với verification process độc lập. Human review có
35/35 quyết định và notes: 15 `Keep Dense`, 13 `Use Cross-Encoder`, bảy
`Tie / Needs review`. User chọn `dense_baseline_v1` ngày 2026-08-15; Cross-Encoder
là evaluated non-selected reranker và không nằm trong MVP runtime path.

Hai review notes ở q-023 và q-041 flag khả năng Ground Truth under-credit evidence
hợp lệ. Không sửa Ground Truth từ reranking experiment; nếu audit phải tạo review
artifact riêng.

Retrieval-only Search API đã hoàn thành và được validation qua ASGI HTTP trên toàn bộ
40 canonical questions. Runtime hiện tại là:

```text
Question -> dense_baseline_v1 -> Top 3 evidence + citation/video metadata
```

Kết quả validation:

| Kiểm tra | Kết quả |
| --- | ---: |
| Answerable Top 3 IDs khớp locked baseline | 35/35 |
| Answerable scores trong absolute tolerance `1e-6` | 35/35 |
| Maximum observed score delta | 0,0000004138 |
| Out-of-scope giữ retrieval-only behavior | 5/5 |
| Repeated response match | 40/40 |
| Video metadata | 38/38 |
| Citation checks | 120/120 |
| HTTP và startup failure cases | 16/16 |
| Cross-process byte-identical artifacts | 6/6 |

Năm out-of-scope questions vẫn trả HTTP `200` và Dense Top 3; response không có
`answer`, `accepted`, `rejected`, `abstain` hoặc `decision`. Đây là behavior đúng của
retrieval-only API, không phải out-of-scope handling.

Top 3 IDs khớp baseline 35/35 chỉ chứng minh API tái tạo đúng locked retriever.
`Recall@3 = 0,742857143` mới là retrieval-quality metric theo Ground Truth; nó không
có nghĩa 35/35 câu đều có evidence đúng trong Top 3.

### Evidence reviewer research closure và active architecture

Phase 8 M2A đã khóa contract/schema và deterministic request package 40 câu theo
flow `Question -> Dense Top 3 -> Evidence accept/reject`. Ground Truth và expected
answer points không lọt vào request gửi reviewer.

Phase 8 M2B đã triển khai local reviewer bằng Ollama `llama3.2:3b`, prompt V1,
structured JSON output. Runtime xử lý đủ 40/40 request và chỉ được chọn supporting
chunk IDs từ Dense Top 3. Runtime này tồn tại và chạy đúng contract, nhưng chưa đạt
production quality gate.

Baseline M3 hoàn thành với 37 câu evaluable và ba exclusion giữ nguyên là q-017,
q-023, q-041:

| Baseline V1 | Kết quả |
| --- | ---: |
| Accept recall | 80,95% |
| False accept rate | 56,25% |
| Evidence-selection precision, all-40 audit | 27/35 = 77,14% |

Trên cùng scope 37 câu evaluable dùng cho prompt experiment, baseline E0 đạt
`27/34 = 79,41%` evidence precision.

Prompt experiment đã khóa E0/E1/E2 trên cùng Dense Top 3 và cùng 37 decision labels.
Human evidence audit cho E2 hoàn thành 38/38 cặp mới: 22 `supports`, 16
`does_not_support`, không có `needs_discussion`.

| Prompt V2 candidate E2 | Kết quả | Ngưỡng | Trạng thái |
| --- | ---: | ---: | --- |
| Accept recall | 90,48% | >= 75% | PASS |
| False accept rate | 56,25% | <= 25% | FAIL |
| Evidence-selection precision, 37-scope | 46/67 = 68,66% | >= 85% | FAIL |

E2 được freeze là `failed_candidate` và không được promote. Đây là kết quả đánh giá
chất lượng, không phải runtime failure: schema/runtime correctness đạt contract,
nhưng decision quality và evidence-selection quality không đạt gate. Recall tăng do
candidate accept nhiều hơn; FAR không giảm và evidence precision thấp hơn baseline.
So sánh cùng 37-scope là E0 `79,41%` và E2 `68,66%`; trên all-40 audit, E0 là
`77,14%` và E2 là `48/70 = 68,57%`.

A1 two-stage experiment giữ nguyên model `llama3.2:3b` nhưng tách requirement
analysis và requirement-level entailment, sau đó dùng deterministic reducer
`accept iff all requirements supported`. Primary/repeat đều đạt runtime `40/40`,
Stage 1/Stage 2/final exact match `40/40`; context thực dùng là `4096` và không có
Ground Truth leakage.

A1 canonical M3 dùng đúng 37 câu evaluable và ba exclusion cũ:

| A1 | Kết quả | Ngưỡng | Trạng thái |
| --- | ---: | ---: | --- |
| Accept recall | 0% | >= 75% | FAIL |
| False accept rate | 0% | <= 25% | PASS |
| Evidence-selection precision | N/A, 0 selected pairs | >= 85% | NOT EVALUABLE |

Confusion matrix A1 là `TP=0, FP=0, FN=21, TN=16`; candidate bị
`reject_class_collapse` và được freeze là `failed_candidate`. FAR `0%` không được
diễn giải là reviewer hữu ích. Stage 2 có 21/103 requirement assessments được đánh
dấu supported, nhưng không câu nào có toàn bộ requirements supported; các ID nội bộ
không được đưa vào final evidence precision.

Ba hướng reviewer đã cho ba kết quả thực nghiệm:

```text
V1 baseline  -> FAR 56,25%, quá permissive
V2 candidate -> FAR 56,25%, evidence precision 68,66%, không cải thiện gate
A1 two-stage -> accept recall 0%, reject collapse
```

Quyết định kiến trúc ngày 2026-08-20: **loại Evidence Reviewer khỏi active runtime
path**. Component được giữ dưới dạng archived experiment với nhãn
`experimental evidence gate — quality threshold not achieved`; toàn bộ code,
human review, metrics, manifests và reports được bảo tồn. Không tiếp tục V2.1, A1.1,
A2, đổi model reviewer hoặc tạo reviewer holdout trong scope project hiện tại.

Active target architecture từ thời điểm này là:

```text
Question
  -> dense_baseline_v1 Top 3
  -> Grounded Answer Generator
       -> Answer + supporting chunk IDs + video URL + timestamp
       -> hoặc Abstain khi Top 3 không đủ bằng chứng
```

Grounded Answer Generator chịu trách nhiệm chỉ dùng Dense Top 3, không dùng kiến
thức ngoài transcript và tự quyết định answer/abstain. Evidence Reviewer quality
gate không còn là dependency chặn downstream.

1. Khóa contract/schema cho grounded answer + abstention trên Dense Top 3.
2. Triển khai một generation stage trả answer hoặc abstain cùng citation metadata.
3. Đánh giá answer groundedness, citation correctness và abstention accuracy
   end-to-end trên canonical 40 câu.
4. q-011, q-024, q-028 và q-036 chỉ được mở lại khi có evidence hoặc quyết định
   human review mới; không chặn active runtime work.

Canonical Gold, embedding/index, retrieval selection, Cross-Encoder evaluation và
Phase 7 Retrieval/Search API đã hoàn thành. Evidence Reviewer research đã kết thúc
và component không nằm trong final runtime architecture. Grounded Answer Generator
và end-to-end groundedness/abstention evaluation chưa được xây.
