# Batch 02 candidate evidence decision record

## Nguồn và phạm vi

- Batch 02 draft: `evaluation/drafts/mit_60001_question_drafts_batch_02.csv`.
- Candidate package: `evaluation/review/batch_02/candidates/batch_02_source_candidates_with_transcript_2026-08-01.csv`.
- Human decision workbook:
  `evaluation/review/batch_02/decisions/batch_02_source_candidates_review_vi_translated.xlsx`.
- Record này chỉ ghi nhận candidate-level decision từ workbook. Nó không tạo
  expected answer points, không đổi `review_status` của draft và không thêm
  record vào canonical JSONL.

## Kết quả import decision

Workbook có 138 dòng candidate cho 30 draft:

| Giá trị `review_decision` đã chuẩn hóa | Số dòng |
| --- | ---: |
| `Được duyệt` / `được duyệt` | 43 |
| `Mơ hồ` | 36 |
| `Sai` / `sai` | 56 |
| Literal không hợp lệ `43` | 3 |

Các giá trị `43` xuất hiện ở q-042 đến q-044. Ba câu này vẫn là out-of-scope
theo `answerable=False` trong draft và `candidate_status=not_applicable_out_of_scope`
trong candidate package; `43` không được diễn giải là một decision review.

## Candidate được human reviewer đánh dấu `Được duyệt`

| Question ID | Candidate ranks được duyệt |
| --- | --- |
| q-016 | 1, 2, 3 |
| q-017 | 4, 5 |
| q-018 | 1 |
| q-019 | 1 |
| q-021 | 2 |
| q-022 | 1, 3, 4, 5 |
| q-023 | 3, 4 |
| q-024 | 1 |
| q-026 | 1, 2 |
| q-027 | 1 |
| q-028 | 5 |
| q-029 | 2 |
| q-030 | 1, 2, 5 |
| q-031 | 2, 4, 5 |
| q-033 | 3 |
| q-034 | 1, 2, 3 |
| q-035 | 1, 5 |
| q-036 | 1 |
| q-037 | 1, 2, 4 |
| q-038 | 3, 5 |
| q-039 | 1, 2 |
| q-040 | 2 |
| q-041 | 3, 5 |

## Câu chưa có candidate được duyệt

| Question ID | Candidate decision trong workbook | Ghi chú có trong workbook |
| --- | --- | --- |
| q-015 | rank 1, 4, 5: `Mơ hồ`; rank 2, 3: `Sai` | rank 1 ghi “nên kết hợp với rank 4”. |
| q-020 | ranks 1–5: `Sai` | Không có candidate được duyệt. |
| q-025 | rank 2: `Mơ hồ`; các rank khác: `Sai` | rank 2 chỉ đúng về cấu trúc inheritance. |
| q-032 | rank 1: `Mơ hồ`; ranks 2–5: `Sai` | rank 1 chỉ nêu definition/handler, chưa nói hậu quả khi không có handler. |

## Ranh giới sau review

`Được duyệt` trong workbook có nghĩa candidate transcript có thể được chọn làm
evidence. Một question có thể có nhiều candidate được duyệt. Workbook không
ghi một danh sách final selected ranks ở question level, vì vậy record này không
tự chọn một range hoặc tự đưa toàn bộ range được duyệt vào canonical dataset.

Theo quyết định của user ngày 2026-08-03, Batch 02 không quay lại vòng tạo
candidate package rồi human review lần nữa. Mọi canonicalization sau này phải
dùng chính candidate decision đã ghi nhận ở đây và vẫn tuân thủ evaluation
contract.
