# Báo cáo ngày 2026-07-26 — Silver transcript cleaning

## Phạm vi

```text
Course: MIT 6.0001 — Introduction to Computer Science and Programming in Python
Term: Fall 2016
Scope version: mit_60001_fall_2016_v1
Target videos: 38
Cleaning version: mit_60001_clean_v1
```

Hôm nay chỉ làm trên target corpus đã chốt. Không crawl thêm, không xóa 286
transcript ngoài scope, không thay đổi Bronze payload và không thay đổi PostgreSQL.

## Công việc hoàn thành

### 1. Audit Bronze target corpus

Đã audit 38 Bronze payload trước khi thiết kế cleaning:

```text
Payloads: 38
Segments: 12.518
Empty segments: 0
Out-of-order timing: 0
Timing overlap pairs: 1.450
Segments có internal newline: 9.048
```

Kết quả này dẫn đến quyết định không normalization text trong v1. Chi tiết:
`BRONZE_SCHEMA_AUDIT.md` và các CSV trong `reports/07_cleaning/`.

### 2. Chốt contract và policy

Đã tạo Silver Transcript Contract, JSON Schema và Cleaning Policy. Policy v1 là
lossless: giữ nguyên từng `segments[].text`, timing, thứ tự segment, language và
`is_generated`. Không decode HTML, collapse whitespace, xóa cue, deduplicate hoặc
sửa code.

Tài liệu:

```text
docs/design/SILVER_TRANSCRIPT_CONTRACT.md
docs/design/SILVER_CLEANING_POLICY.md
schemas/silver_transcript_v1.schema.json
docs/decisions/SILVER_STORAGE_DECISION.md
```

### 3. Sample validation

Đã build năm video đại diện, gồm transcript ngắn nhất, dài nhất, code-heavy,
language variant và caption cue/duplicate. Toàn bộ validation pass. Hai Python
process độc lập tạo cùng SHA-256 cho sample output.

### 4. Full Silver build

Đã build toàn bộ 38 video bằng shared builder, không dùng implementation copy riêng
cho full corpus.

| Kiểm tra | Kết quả |
| --- | ---: |
| Silver record | 38/38 |
| Video ID duy nhất | 38 |
| Position | 0–37 |
| Tổng segment | 12.518 |
| Validation thất bại | 0 |
| Cross-process byte determinism | passed |

SHA-256 của full output:

```text
50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb
```

## Output và bằng chứng

```text
scripts/cleaning/silver_builder.py
scripts/cleaning/build_silver_sample.py
scripts/cleaning/build_silver_full.py
scripts/cleaning/verify_silver_sample_cross_process.py
reports/07_cleaning/bronze_schema_audit.csv
reports/07_cleaning/bronze_payload_profile.csv
reports/07_cleaning/bronze_audit_summary.csv
reports/07_cleaning/sample_validation.csv
reports/07_cleaning/sample_cross_process_validation.csv
reports/07_cleaning/full_validation.csv
reports/07_cleaning/cleaning_summary.csv
```

Silver output `data/silver/mit_60001/transcripts_clean.jsonl` là generated data và
không commit. Các CSV report không chứa transcript text hoặc segment text.

## Trạng thái và bước tiếp theo

Phase 4 — Transcript cleaning đã hoàn thành. Chưa thực hiện chunking, embedding,
vector index, retrieval API hoặc evaluation. Milestone kế tiếp là thiết kế chunking
experiment trên Silver v1 và tạo baseline để so sánh semantic chunking.
