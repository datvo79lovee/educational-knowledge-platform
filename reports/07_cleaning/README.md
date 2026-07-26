# Silver transcript cleaning reports

Folder này chứa audit Bronze schema, sample validation và kết quả cleaning của
target corpus MIT 6.0001.

Output của Milestone 1:

```text
bronze_schema_audit.csv
bronze_payload_profile.csv
bronze_audit_summary.csv
```

Các CSV chỉ chứa schema, metadata và chỉ số tổng hợp. Không file nào chứa
transcript text hoặc segment text.

Tạo lại report bằng:

```powershell
python -X utf8 scripts/cleaning/audit_target_bronze.py
```

Cleaning policy:

```text
docs/design/SILVER_CLEANING_POLICY.md
```

Sample Silver build:

```text
data/silver/mit_60001/samples/transcripts_clean_sample.jsonl
sample_validation.csv
sample_cross_process_validation.csv
```

Tạo và validate đúng năm sample bằng:

```powershell
python -X utf8 scripts/cleaning/build_silver_sample.py
```

Sample JSONL là generated data trong `data/silver/` và không được commit. CSV
validation không chứa transcript text.

Xác minh hai Python process độc lập tạo byte giống nhau:

```powershell
python -X utf8 scripts/cleaning/verify_silver_sample_cross_process.py
```

Full Silver build (38 video trong target manifest):

```powershell
python -X utf8 scripts/cleaning/build_silver_full.py
```

Output và report có thêm:

```text
data/silver/mit_60001/transcripts_clean.jsonl
full_validation.csv
cleaning_summary.csv
```

`full_validation.csv` có một dòng metadata/validation cho mỗi video;
`cleaning_summary.csv` tổng kết 38 record, tổng segment và SHA-256 của toàn file.
Cả hai không chứa transcript text.
