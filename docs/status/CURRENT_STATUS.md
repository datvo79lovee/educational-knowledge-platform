# Trạng thái hiện tại

## Ngày ghi nhận

2026-08-25

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

## Vietnamese runtime contract

```text
question_vi
  → literal translator (Ollama llama3.2:3b)
  → retrieval_query English
  → Dense Top 3
  → G0 + answer_language=vi
  → Vietnamese answer + application-owned citations
```

`POST /answer` nhận `answer_language: "en" | "vi"` và trả thêm `original_query`,
`retrieval_query`, `answer_language`. Nhánh English giữ prompt Reliability V1
**byte-identical** (`grounded_answer_prompt_v1`, sha `2b0a35d6…`) và không gọi
translator. Translator lỗi thì runtime **fail-closed**, không âm thầm đem câu tiếng
Việt đi Dense retrieval.

## Bounded local demo

Demo cục bộ đã validate `GET /`,
`GET /static/app.js`, `POST /search`, `GET /videos/{video_id}` và `POST /answer` cho
cả English/Vietnamese đều trả response contract hợp lệ. `/answer` chỉ được smoke sau
khi local Ollama `llama3.2:3b` khớp exact digest
`a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`.

Demo chỉ là static client của `/answer`: không thay Dense/index/scoring, prompt,
translator hay citation mapping. Smoke xác minh request path và shape response, không
là đánh giá chất lượng mới. Chi tiết behavior/source hashes tại
`reports/36_bounded_local_demo/`.
