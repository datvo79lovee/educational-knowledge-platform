# PostgreSQL transcript load validation

Folder này chứa kết quả kiểm tra sau khi load transcript vào PostgreSQL.

Output:

```text
validation_summary.csv
target_transcript_validation.csv
```

`validation_summary.csv` lưu các count và trạng thái pass/fail.
`target_transcript_validation.csv` lưu metadata và độ dài transcript của 38 target
videos. Không file nào trong folder này chứa `raw_text`.

Tạo lại report bằng:

```powershell
python -X utf8 scripts/transcript_loading/validate_target_postgresql.py
```
