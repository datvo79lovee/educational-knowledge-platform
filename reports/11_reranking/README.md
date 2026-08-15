# Cross-Encoder reranking reports

Folder này chứa experiment rerank Dense Top 50 bằng Cross-Encoder, validation,
human review và quyết định cấu hình cho canonical MIT 6.0001 corpus.

## Contract đã khóa

```text
Dense candidates : Top 50 từ dense_baseline_v1
Reranker          : cross-encoder/ms-marco-MiniLM-L6-v2
Revision          : c5ee24cb16019beea0893ab7796b1df96625c6b8
Device            : CPU
Batch size        : 16
Max length        : 512
Output            : Top 3
Tie-break         : score desc, Dense rank asc, chunk ID asc
Questions         : 35 answerable
Ground Truth      : 57 ranges
```

Model cache là generated data trong `data/models/` và không được commit.

## Lệnh chạy

Lần đầu, cho phép tải đúng model revision đã khóa:

```powershell
python -X utf8 scripts/retrieval/evaluate_cross_encoder_reranking.py --allow-model-download
```

Các lần sau chỉ dùng cache local:

```powershell
python -X utf8 scripts/retrieval/evaluate_cross_encoder_reranking.py
python -X utf8 scripts/retrieval/verify_cross_encoder_reranking_cross_process.py
```

## Kết quả

| Method | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dense_baseline_v1` | 0,573585434 | 0,371428571 | 0,742857143 | 0,857142857 | 0,914285714 |
| `cross_encoder_ms_marco_minilm_l6_v2` | 0,532611871 | 0,342857143 | 0,657142857 | 0,771428571 | 0,914285714 |

Dense Top 50 chứa first relevant và đầy đủ Ground Truth evidence cho 35/35 câu.
Không có input pair nào bị truncate; độ dài lớn nhất là 214 tokens. Năm report
artifact byte-identical giữa M2 và Python verification process độc lập.

## Human review và quyết định

Workbook reviewed có đủ 35/35 quyết định và 35 review notes:

```text
Keep Dense          : 15
Use Cross-Encoder   : 13
Tie / Needs review  : 7
```

User chọn `dense_baseline_v1` ngày 2026-08-15. Cross-Encoder được giữ làm evaluated
non-selected reranker. Raw comparison tiếp tục giữ `pending_human_decision` vì đây
là deterministic output đã khóa; decision CSV riêng là nguồn trạng thái sau review.

Hai review notes ở q-023 và q-041 nêu khả năng Ground Truth đang under-credit evidence
hợp lệ. Đây là audit item riêng; không sửa Ground Truth từ reranking experiment.

## Artifact

```text
cross_encoder_reranking_results.csv
cross_encoder_reranking_comparison.csv
cross_encoder_reranking_question_comparison.csv
cross_encoder_reranking_validation.csv
cross_encoder_reranking_manifest.json
cross_encoder_reranking_cross_process_validation.csv
reranking_configuration_decision_2026-08-15.csv
```

Bước tiếp theo là xây Retrieval/Search API dùng selected Dense baseline và trả Dense
Top 3 evidence. Cross-Encoder không nằm trong MVP runtime path hiện tại.
