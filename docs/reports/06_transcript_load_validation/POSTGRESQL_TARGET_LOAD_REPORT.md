# Báo cáo load transcript mục tiêu vào PostgreSQL

## Ngày thực hiện

2026-07-25

## Phạm vi

```text
Course: MIT 6.0001
Term: Fall 2016
Scope version: mit_60001_fall_2016_v1
Target videos: 38
```

Mục tiêu của bước này là xác nhận 34 transcript mới trong Bronze đã được load vào
PostgreSQL và toàn bộ 38 target videos có transcript hợp lệ.

## Loader

```text
scripts/transcript_loading/load_transcripts_to_postgresql.py
```

Loader được chạy với `--commit`, sau đó chạy lại ở chế độ dry-run để kiểm tra tính
idempotent.

## Kết quả load

```text
Input records    : 324
Already existing : 290
Inserted         : 34
Before count     : 290
After count      : 324
```

PostgreSQL đã tăng từ 290 lên 324 transcript.

## Kết quả target validation

| Chỉ số | Kết quả |
| --- | ---: |
| Tổng transcript trong PostgreSQL | 324 |
| Target manifest videos | 38 |
| Target JOIN rows | 38 |
| Target video ID duy nhất | 38 |
| Thiếu metadata video | 0 |
| Thiếu target transcript | 0 |
| Target transcript bị trùng | 0 |
| `raw_text` rỗng | 0 |
| `language` rỗng | 0 |

Transcript length:

```text
Minimum : 653 ký tự
Maximum : 49.645 ký tự
Average : 13.243 ký tự
```

Transcript ngắn nhất vẫn có nội dung và không vi phạm điều kiện dữ liệu rỗng.
Độ dài chỉ được dùng như chỉ số profiling, chưa phải tiêu chí đánh giá chất lượng
nội dung.

## Script validation

```text
scripts/transcript_loading/validate_target_postgresql.py
```

Script thực hiện kết nối PostgreSQL read-only, đọc 38 ID từ target manifest và
JOIN với `videos`, `transcripts`. Script không hard-code danh sách video ID và
không ghi database.

Chạy lại:

```powershell
python -X utf8 scripts/transcript_loading/validate_target_postgresql.py
```

## File đầu ra

```text
reports/06_transcript_load_validation/validation_summary.csv
reports/06_transcript_load_validation/target_transcript_validation.csv
```

CSV chi tiết chỉ chứa metadata, language, transcript length và retrieved time.
Không xuất `raw_text` ra report.

## Kết luận

PostgreSQL load hợp lệ. Corpus MIT 6.0001 Fall 2016 đạt transcript coverage 38/38,
không có dữ liệu rỗng, video thiếu hoặc transcript trùng.

Milestone tiếp theo là cập nhật project status và đóng Phase PostgreSQL Load trước
khi thiết kế Silver transcript schema.
