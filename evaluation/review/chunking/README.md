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

Các raw retrieval outputs và manifest của experiment chunking trước đây đã được
retire khỏi public repository. Trạng thái human review và configuration được chọn
được giữ lại trong decision workbook/CSV của folder này cho mục đích lịch sử.

Canonical Gold full hiện được rebuild trực tiếp bằng canonical chunking config và
`scripts/chunking/build_canonical_gold.py`; không cần chạy lại historical selection
hoặc retrieval experiment.
