# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-24

## Pipeline canonical

```text
YouTube API → Bronze → Silver → Gold
                         ↓
          lineage / hashes / schema validation / checkpoint-resume
                         ↓
             embedding / canonical Dense index
                         ↓
                  Dense Top 3 Search API
                         ↓
         G0 Grounded Answer Generator (llama3.2:3b)
                         ↓
      deterministic normalization → Pydantic validation
                         ↓
       application-owned citations → API response
```

## Corpus và benchmark

- Corpus mục tiêu: MIT 6.0001 Fall 2016, 38 video.
- Silver: 38/38 video, 12.518 segments.
- Canonical Gold: 861 chunks.
- Dense index: exact cosine, 861 × 384.
- Benchmark canonical: 40 câu approved; 35 answerable, 5 out-of-scope, 57 Ground
  Truth time ranges.
- Provenance benchmark được khóa tại
  `evaluation/mit_60001/benchmark_manifest.json`; validator kiểm tra schema,
  counts, reviewer-batch summary và SHA-256 của benchmark/schema.

## Retrieval và API

- Retriever canonical: `dense_baseline_v1`, Top 3 evidence.
- `POST /search` là retrieval-only.
- `POST /answer` gọi chính Dense Top 3, không gọi stage reviewer trung gian.
- Citation URL/timestamp do application dựng từ metadata của chunk; LLM không tự
  tạo citation.

## Grounded Answer G0 / Reliability V1

G0 là baseline canonical hiện tại, không phải production-ready claim.

| Metric | Kết quả |
| --- | ---: |
| Public runtime success | 40/40 |
| Decision accuracy | 23/37 = 62,16% |
| False abstain | 11/21 evidence-sufficient |
| False answer | 3/16 evidence-insufficient |
| Answer precision | 76,92% |
| Strict end-to-end | 17/37 = 45,95% |

Reliability normalization là behavior runtime có chủ đích: chỉ canonicalize literal
abstain thành `null` và deduplicate ID hợp lệ thuộc Dense Top 3. Pydantic vẫn là
final validator. Final metrics, results và manifest nằm tại
`reports/25_grounded_answer_reliability_v1/`; canonical human judgments nằm tại
`evaluation/review/grounded_answer/grounded_answer_reliability_v1_human_review_canonical.csv`.

## Thành phần đã loại

Evidence Reviewer, BM25, Hybrid RRF, Cross-Encoder và G1 prompt experiment không
còn code, test, report hoặc artifact trong working tree. Lý do chọn Dense/G0 được
tóm tắt tại `docs/decisions/CANONICAL_RUNTIME_DECISIONS.md`; Git history giữ lịch
sử development trước cleanup.

## Phase 9 — Multilingual Retrieval Baseline

Phase 9 đã complete và freeze trên 20 paired semantic intents. Ba representation
`question_en`, `question_vi` và frozen `literal_en` dùng cùng canonical Ground
Truth; human review M1 hoàn thành 20/20 với 19 `Equivalent`, 1
`Minor wording difference` (`mit60001-q-008`) và 0 `Semantic drift`.

M2 chạy đúng hai branches trên cùng `dense_baseline_v1`, canonical Gold/index và
full ranking 861:

```text
question_en → Dense
literal_en  → Dense
```

M2 có 40/40 retrieval records, 0 translator/LLM/generator call và deterministic
rerun PASS. M3 chỉ đọc frozen M1 + M2, không rerun retrieval hoặc sửa Ground Truth.

| Metric | EN canonical | VI → literal EN | Δ VI - EN |
| --- | ---: | ---: | ---: |
| MRR | 0,596274510 | 0,634226651 | +0,037952141 |
| Recall@1 | 0,400000000 | 0,550000000 | +0,150000000 |
| Recall@3 | 0,750000000 | 0,700000000 | -0,050000000 |
| Recall@5 | 0,800000000 | 0,750000000 | -0,050000000 |
| Full Evidence@3 | 0,500000000 | 0,550000000 | +0,050000000 |

First relevant rank có 4 intents improved, 10 unchanged và 6 degraded. Mean Top-3
overlap là 0,80; exact ordered Top-3 match là 6/20. Hai exact-string controls
`mit60001-q-003` và `mit60001-q-022` PASS.

Kết luận khóa: literal English translation preserved overall Dense retrieval
quality trên paired benchmark 20 intents, với mixed per-intent effects và không có
bằng chứng systematic degradation. Không diễn giải Vietnamese retrieval tốt hơn
English hoặc translation luôn làm retrieval kém đi.

Toàn bộ giảm 0,05 ở Recall@3/@5 đến từ `mit60001-q-008`, câu duy nhất có review
`Minor wording difference`: first relevant rank 2 → 7 và Top-3 overlap 0/3. Đây là
observed sensitivity về translation fidelity (`object` → `value`), không phải bằng
chứng cần fusion. Không sửa translation hậu nghiệm và không tune theo một failure
case đơn lẻ.

Quyết định sau M3: không mở `expanded_en`, query expansion, BM25, Hybrid RRF,
reranking hoặc model comparison. Phase 9 chuyển từ retrieval research sang runtime
integration.

## Bước tiếp theo

Multilingual Runtime Integration V1, chưa triển khai:

```text
Vietnamese user query
  → original_query
  → literal English translator
  → retrieval_query
  → Dense Top 3
  → G0 Grounded Answer Generator + answer_language=vi
  → Vietnamese answer + application-owned citations
```

Runtime contract tương lai cần phân biệt `original_query`, `retrieval_query` và
`answer_language`. Không sửa Dense retriever và không thêm BM25/RRF/reranker.
