# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-23

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

## Bước tiếp theo

Phase 9 — multilingual retrieval baseline:

```text
EN canonical query → Dense
VI query → literal English translation → Dense
```

So sánh trên cùng Ground Truth/relevant chunks, với MRR, Recall@1, Recall@3,
Recall@5 và Full Evidence@3. Chưa mở expanded translation, query expansion, RRF,
reranking hoặc prompt tuning generator.
