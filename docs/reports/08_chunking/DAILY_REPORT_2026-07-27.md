# Báo cáo ngày 2026-07-27 — Chunking experiment design và sample

## Phạm vi

```text
Course: MIT 6.0001 Fall 2016
Scope version: mit_60001_fall_2016_v1
Input: Silver v1, 38 video target
Sample: 5 video đại diện
Encoder: sentence-transformers/all-MiniLM-L6-v2
Encoder revision: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
```

Không thay đổi Bronze, Silver, PostgreSQL hoặc 286 transcript ngoài scope. Không tạo
Gold full corpus 38 video, embedding index hay retrieval API.

## Công việc hoàn thành

### 1. Gold contract và schema

Đã tạo Gold chunk contract và JSON Schema. Mỗi Gold chunk phải giữ source segment
range, text lossless, citation timing, Silver content hash lineage và content hash
của chính chunk. `end_second` dùng Decimal cho giá trị dẫn xuất để tránh float artifact.

### 2. Thiết kế experiment

Ba configuration dùng cùng Gold contract:

| Configuration | Strategy | Chunks sample | Token max quan sát |
| --- | --- | ---: | ---: |
| `fixed_wp240_o48_v1` | Fixed-token baseline | 178 | 240 |
| `semantic_cosine_wp240_v1` | Semantic cosine, không overlap | 285 | 192 |
| `semantic_cosine_wp192_o32_v1` | Semantic cosine, overlap nhẹ | 350 | 188 |

Semantic strategy chỉ chọn boundary giữa các Silver segment bằng cosine similarity
của semantic window. Nó không dùng LLM, không sửa text, không tóm tắt và không tạo
topic label.

### 3. Sample validation

Sample gồm năm video đã chọn từ Silver validation. Cả ba configuration pass:

```text
Source segment coverage: complete
Duplicate chunk ID: 0
Schema errors: 0
Non-tail undersize chunks: 0
Oversize multi-segment chunks: 0
In-process rebuild: deterministic
Cross-process byte determinism: passed
```

Cross-process verification chạy hai Python process độc lập. SHA-256 khớp cho cả ba
Gold sample JSONL; chi tiết nằm trong report CSV.

### 4. Evaluation contract

Đã tạo schema và template trống cho 40–60 câu hỏi. AI-generated question chỉ là
`draft`; chỉ question được người hiểu Python review là `approved` mới được dùng để
chọn configuration. Hiện chưa có question approved, do đó không có Recall@k, MRR hay
citation correctness để so sánh ba configuration.

## Output

```text
docs/design/GOLD_CHUNK_CONTRACT.md
docs/design/CHUNKING_EXPERIMENT.md
docs/design/CHUNKING_EVALUATION_CONTRACT.md
schemas/gold_chunk_v1.schema.json
schemas/chunking_evaluation_question_v1.schema.json
scripts/chunking/build_chunk_samples.py
scripts/chunking/verify_chunk_samples_cross_process.py
reports/08_chunking/sample_chunk_validation.csv
reports/08_chunking/sample_chunk_cross_process_validation.csv
evaluation/templates/mit_60001_evaluation_questions_template.csv
```

Gold sample JSONL nằm trong `data/gold/mit_60001/samples/` và bị gitignore. Các CSV
report không chứa chunk text, transcript text hoặc embedding vector.

## Kết luận và bước tiếp theo

Sample pipeline hợp lệ về schema, lineage, coverage, token guardrail và determinism.
Nó chưa chứng minh semantic configuration tốt hơn fixed baseline. Bước tiếp theo là
soạn và review evaluation questions, rồi chạy retrieval comparison trước khi duyệt
full Gold build 38 video.
