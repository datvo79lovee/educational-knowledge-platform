# MIT 6.0001 chunking human review

Folder này lưu human citation review và quyết định chọn configuration cho
MIT 6.0001 chunking experiment.

## Artifact có hiệu lực

- Human review cuối cùng:
  `mit_60001_chunking_citation_review_2026-08-11_reaudited.xlsx`
- Quyết định configuration:
  `mit_60001_chunking_configuration_decision_2026-08-12.csv`

Template ban đầu và vòng review trước re-audit đã được xóa trong repository cleanup;
chỉ re-audit final được giữ.

## Quyết định

Configuration được human approve ngày 2026-08-12:

```text
semantic_cosine_wp240_v1
```

Re-audit đủ 35 câu answerable ghi nhận:

| Configuration | Correct | Partial | Incorrect | Boundary Good | Preferred |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_wp240_o48_v1` | 28 | 6 | 1 | 4 | 4 |
| `semantic_cosine_wp240_v1` | 28 | 7 | 0 | 24 | 16 |
| `semantic_cosine_wp192_o32_v1` | 25 | 10 | 0 | 20 | 14 |

Có một câu `Tie`. Workbook đã pass kiểm tra 35 unique question ID, cùng question set
giữa ba configuration, không thiếu decision, không có giá trị ngoài contract và
`Final_decision` khớp ba sheet nguồn.

`reports/08_chunking/chunking_comparison.csv` là raw deterministic retrieval output;
field `manual_citation_review_status=pending` trong file đó không được sửa tay vì sẽ
làm sai cross-process hash. Trạng thái human review và configuration được chọn phải
đọc từ decision CSV trong folder này.

Canonical Gold full đã được build tại `data/gold/mit_60001/chunks.jsonl` từ
configuration đã chọn. Output có 861 chunks trên 38 video, phủ đủ 12.518 Silver
segments và byte-identical với selected candidate. Manifest và validation reports
nằm trong `reports/08_chunking/`.
