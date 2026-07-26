# Báo cáo full Silver build

## Ngày thực hiện

2026-07-26

## Phạm vi

```text
Course: MIT 6.0001
Term: Fall 2016
Scope version: mit_60001_fall_2016_v1
Cleaning version: mit_60001_clean_v1
```

Build chỉ đọc target manifest, Bronze JSONL và Silver JSON Schema. Nó không thay
đổi Bronze, PostgreSQL hoặc transcript source.

## Cách build

`scripts/cleaning/build_silver_full.py` gọi shared core
`scripts/cleaning/silver_builder.py` với selection là toàn bộ manifest. Core:

- yêu cầu đúng 38 record và position liên tục từ 0 đến 37;
- tạo Silver lossless theo `SILVER_CLEANING_POLICY.md`;
- kiểm tra JSON Schema, metadata manifest, text/timing so với Bronze, lineage hash,
  content hash và invariant;
- build độc lập hai lần trong process trước khi ghi output atomically.

Full builder được chạy hai lần ở hai Python process riêng. SHA-256 của file output
sau mỗi lần giống nhau, nên đây là kiểm tra byte determinism ở cấp process, không
chỉ là serialize lại cùng object trong bộ nhớ.

## Kết quả validation

| Kiểm tra | Kết quả |
| --- | ---: |
| Record Silver | 38/38 |
| Video ID duy nhất | 38 |
| Position | 0–37 |
| Tổng segment | 12.518 |
| Record validation thất bại | 0 |
| Schema valid | 38/38 |
| Bronze text equal | 38/38 |
| Timing equal | 38/38 |
| Source hash valid | 38/38 |
| Content hash valid | 38/38 |
| In-process independent rebuild | 38/38 |
| Cross-process byte determinism | passed |

SHA-256 của full output:

```text
50d559529bedc33715b13312c5e4b7def80ac808521b53699a14465e084a8ecb
```

## Output

```text
data/silver/mit_60001/transcripts_clean.jsonl
reports/07_cleaning/full_validation.csv
reports/07_cleaning/cleaning_summary.csv
```

Silver JSONL là generated data trong thư mục `data/silver/` và bị gitignore.
Hai CSV report không chứa transcript text hoặc segment text.

## Kết luận

Phase 4 hoàn thành cho cleaning version `mit_60001_clean_v1`. Silver v1 giữ nguyên
text và timing của Bronze; nó chưa thực hiện semantic chunking. Bước tiếp theo là
thiết kế và đánh giá chunking experiment trên Silver này.
