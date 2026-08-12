# Embedding/index reports

Folder này chứa audit metadata và retrieval validation cho exact dense index của
canonical MIT 6.0001 Gold chunks. Report không chứa `chunk_text` hoặc embedding vector.

Generated index nằm tại `data/indexes/mit_60001/` và bị gitignore:

```text
embeddings.npy
metadata.jsonl
```

## Build và validation

Build lại index từ canonical Gold:

```powershell
python -X utf8 scripts/embedding/build_mit_60001_index.py
```

Xác minh bốn index artifact byte-identical qua hai Python processes:

```powershell
python -X utf8 scripts/embedding/verify_index_cross_process.py
```

Chạy retrieval trên production index bằng 35 canonical answerable questions:

```powershell
python -X utf8 scripts/embedding/evaluate_index_retrieval.py
```

Xác minh ba retrieval report byte-identical qua hai Python processes:

```powershell
python -X utf8 scripts/embedding/verify_index_retrieval_cross_process.py
```

## Artifact

```text
embedding_index_manifest.json
embedding_index_validation.csv
embedding_index_cross_process_validation.csv
production_index_retrieval_results.csv
production_index_retrieval_comparison.csv
production_index_retrieval_manifest.json
production_index_retrieval_cross_process_validation.csv
```

Index hiện tại dùng `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, exact cosine trên ma trận float32
L2-normalized có shape `861 x 384`.

Production retrieval khớp dense baseline ở toàn bộ metrics, Top 10 chunk IDs 35/35
và Top 10 scores 35/35. Kết quả chính:

| Metric | Kết quả |
| --- | ---: |
| MRR | 0,573585434 |
| Recall@1 | 0,371428571 |
| Recall@3 | 0,742857143 |
| Recall@5 | 0,857142857 |
| Recall@10 | 0,914285714 |
