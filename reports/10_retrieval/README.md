# Lexical and Hybrid retrieval reports

Folder này chứa BM25 index audit, Dense/BM25/RRF comparison và human configuration
decision cho canonical MIT 6.0001 corpus. Report không chứa `chunk_text` hoặc vector.

Generated lexical index nằm tại `data/indexes/mit_60001/lexical_index.json` và bị
gitignore.

## Build và validation

Build exact BM25 index:

```powershell
python -X utf8 scripts/retrieval/build_mit_60001_lexical_index.py
```

Xác minh lexical index qua hai process:

```powershell
python -X utf8 scripts/retrieval/verify_lexical_index_cross_process.py
```

Chạy Dense/BM25/equal-weight RRF comparison:

```powershell
python -X utf8 scripts/retrieval/evaluate_hybrid_retrieval.py
```

Xác minh retrieval reports qua hai process:

```powershell
python -X utf8 scripts/retrieval/verify_hybrid_retrieval_cross_process.py
```

## Artifact

```text
lexical_index_manifest.json
lexical_index_validation.csv
lexical_index_cross_process_validation.csv
hybrid_retrieval_results.csv
hybrid_retrieval_comparison.csv
hybrid_retrieval_question_comparison.csv
hybrid_retrieval_manifest.json
hybrid_retrieval_cross_process_validation.csv
retrieval_configuration_decision_2026-08-14.csv
```

## Kết quả và quyết định

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `bm25_v1` | 0,443842416 | 0,257142857 | 0,600000000 | 0,628571429 | 0,714285714 |
| `hybrid_rrf_k60_d100_v1` | 0,517862148 | 0,342857143 | 0,571428571 | 0,828571429 | 0,914285714 |

User chọn `dense_baseline_v1` ngày 2026-08-14. BM25 và equal-weight RRF được giữ làm
evaluated non-selected baselines. Raw comparison vẫn giữ
`selection_status=pending_human_decision` vì file đó là deterministic output đã khóa
bằng cross-process hash; decision CSV riêng là nguồn trạng thái sau human review.
