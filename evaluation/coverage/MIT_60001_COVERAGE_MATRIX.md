# MIT 6.0001 Coverage Matrix

## Phạm vi và quy ước

- Batch 01 chỉ đếm 13 record `approved` hiện có trong `evaluation/mit_60001/evaluation_questions.jsonl`.
- Batch 02 đếm 30 record `draft` trong `evaluation/drafts/mit_60001_question_drafts_batch_02.csv`. Chúng chưa có source evidence và chưa được dùng làm evaluation.
- Một câu có thể xuất hiện ở nhiều concept khi wording của chính câu đó kiểm tra nhiều concept. Vì vậy tổng các hàng không phải số câu duy nhất.
- Đây là artifact quản lý coverage theo wording câu hỏi; không phải bằng chứng transcript. Chỉ source review mới xác nhận câu answerable và evidence range.

## Matrix hiện tại

| Concept | Batch 01 approved | Batch 02 draft | Total | Question IDs |
| --- | ---: | ---: | ---: | --- |
| Computation / course orientation | 2 | 0 | 2 | q-001, q-002 |
| Variables / binding / scope | 5 | 0 | 5 | q-003, q-004, q-007, q-008, q-009 |
| Branching / Boolean comparisons | 0 | 1 | 1 | q-021 |
| Loops | 0 | 1 | 1 | q-027 |
| Strings | 0 | 2 | 2 | q-020, q-027 |
| Functions / abstraction | 1 | 3 | 4 | q-009, q-023, q-029, q-033 |
| Lists / mutation / indexing | 2 | 4 | 6 | q-010, q-014, q-022, q-026, q-031, q-035 |
| Dictionaries | 1 | 2 | 3 | q-014, q-022, q-024 |
| Recursion | 1 | 0 | 1 | q-005 |
| Testing / debugging | 0 | 3 | 3 | q-018, q-034, q-039 |
| Assertions | 0 | 3 | 3 | q-016, q-028, q-040 |
| Exceptions | 0 | 3 | 3 | q-017, q-032, q-040 |
| OOP / classes / inheritance | 0 | 4 | 4 | q-025, q-030, q-036, q-041 |
| Program efficiency | 1 | 2 | 3 | q-006, q-019, q-037 |
| Searching | 0 | 3 | 3 | q-019, q-037, q-038 |
| Sorting | 0 | 1 | 1 | q-038 |
| Out-of-scope controls | 2 | 3 | 5 | q-012, q-013, q-042, q-043, q-044 |

## Quy tắc cập nhật

Mỗi lần thêm, thay wording, chấp nhận hoặc loại một evaluation question, cập nhật hàng concept liên quan, số đếm và Question IDs trong matrix này cùng milestone đó. Không chuyển một câu `draft` sang cột Batch 01 approved cho đến khi canonical JSONL có record `approved` với source evidence đã được review.
