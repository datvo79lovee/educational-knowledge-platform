# Chunking experiment reports

Folder này chứa validation metadata cho Gold chunk sample của MIT 6.0001. Report
không chứa `chunk_text`, Silver transcript text hoặc embedding vector.

```text
sample_chunk_validation.csv
sample_chunk_cross_process_validation.csv
```

`sample_chunk_validation.csv` ghi metrics và validation của ba configuration trên năm
video sample. `sample_chunk_cross_process_validation.csv` xác minh hai Python process
độc lập tạo cùng SHA-256 cho từng configuration.

Tạo lại sample và validation trong process:

```powershell
python -X utf8 scripts/chunking/build_chunk_samples.py
```

Xác minh cross-process:

```powershell
python -X utf8 scripts/chunking/verify_chunk_samples_cross_process.py
```

Gold JSONL tương ứng nằm trong `data/gold/mit_60001/samples/` và bị gitignore.
