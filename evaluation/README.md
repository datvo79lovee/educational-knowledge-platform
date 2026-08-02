# Evaluation workspace

## Nhìn nhanh

`evaluation/` chỉ chứa artifact phục vụ xây dựng và kiểm tra benchmark MIT 6.0001.
Mỗi batch được tách riêng để candidate, quyết định human review và ghi chú không
lẫn vào nhau.

```text
evaluation/
├── mit_60001/                         # Canonical approved dataset
├── templates/                         # Template/schema-facing review input
├── drafts/                            # Question draft, chưa có source evidence
├── coverage/                          # Coverage Matrix theo concept
└── review/
    ├── batch_01/
    │   ├── candidates/                # Candidate retrieval lịch sử và v2 hiện hành
    │   ├── decisions/                 # Human decision CSV/XLSX
    │   └── BATCH_01_*.md              # Review notes và additional evidence
    └── batch_02/
        ├── candidates/                # Candidate package có transcript context
        ├── decisions/                 # Human decision workbook
        └── BATCH_02_CONTENT_REVIEW.md # Decision record có thể audit
```

## Artifact hiện hành

| Mục đích | File |
| --- | --- |
| Canonical approved subset | `mit_60001/evaluation_questions.jsonl` |
| Batch 01 current source candidates | `review/batch_01/candidates/batch_01_source_candidates_with_transcript_2026-07-31_v2.csv` |
| Batch 01 human decisions | `review/batch_01/decisions/batch_01_review_vi_with_decision.xlsx` |
| Batch 02 candidate package | `review/batch_02/candidates/batch_02_source_candidates_with_transcript_2026-08-01.csv` |
| Batch 02 human decisions | `review/batch_02/decisions/batch_02_source_candidates_review_vi_translated.xlsx` |
| Coverage Matrix | `coverage/MIT_60001_COVERAGE_MATRIX.md` |

## Quy tắc trạng thái

- `drafts/` là candidate chưa kiểm source; không dùng cho evaluation hoặc metrics.
- Chỉ record `approved` trong `mit_60001/evaluation_questions.jsonl` được dùng
  để chọn configuration hoặc tính retrieval metrics.
- Candidate CSV và workbook human review là artifact review, không phải canonical
  evidence. Không tự chuyển candidate rank thành Ground Truth.
- Workbook human review phải được lưu trong `review/<batch>/decisions/`; Markdown
  và report chỉ tham chiếu path bên trong project.

Chi tiết contract: `docs/design/CHUNKING_EVALUATION_CONTRACT.md` và
`docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md`.
