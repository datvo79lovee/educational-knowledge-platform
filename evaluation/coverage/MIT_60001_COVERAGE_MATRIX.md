# MIT 6.0001 Coverage Matrix

## Phạm vi và quy ước

- Batch 01 đếm 13 record `approved` hiện có trong `evaluation/mit_60001/evaluation_questions.jsonl`.
- Batch 02 có 27 record `approved` đã qua human review và đã được canonicalize; ba draft bị human review `Reject` chưa phải canonical evaluation.
- Một câu có thể xuất hiện ở nhiều concept khi wording của chính câu đó kiểm tra nhiều concept. Vì vậy tổng các hàng không phải số câu duy nhất.
- Đây là artifact quản lý coverage theo wording câu hỏi; không phải bằng chứng transcript. Chỉ source review mới xác nhận câu answerable và evidence range.

## Matrix hiện tại

| Concept | Batch 01 approved | Batch 02 approved | Batch 02 chưa canonical | Approved total | Question IDs |
| --- | ---: | ---: | ---: | ---: | --- |
| Computation / course orientation | 2 | 1 | 0 | 3 | approved: q-001, q-002, q-015 |
| Variables / binding / scope | 5 | 0 | 0 | 5 | approved: q-003, q-004, q-007, q-008, q-009 |
| Branching / Boolean comparisons | 0 | 1 | 0 | 1 | approved: q-021 |
| Loops | 0 | 1 | 0 | 1 | approved: q-027 |
| Strings | 0 | 2 | 0 | 2 | approved: q-020, q-027 |
| Functions / abstraction | 1 | 3 | 0 | 4 | approved: q-009, q-023, q-029, q-033 |
| Lists / mutation / indexing | 2 | 4 | 0 | 6 | approved: q-010, q-014, q-022, q-026, q-031, q-035 |
| Dictionaries | 1 | 1 | 1 | 2 | approved: q-014, q-022; chưa canonical: q-024 |
| Recursion | 1 | 0 | 0 | 1 | approved: q-005 |
| Testing / debugging | 0 | 3 | 0 | 3 | approved: q-018, q-034, q-039 |
| Assertions | 0 | 2 | 1 | 2 | approved: q-016, q-040; chưa canonical: q-028 |
| Exceptions | 0 | 3 | 0 | 3 | approved: q-017, q-032, q-040 |
| OOP / classes / inheritance | 0 | 3 | 1 | 3 | approved: q-025, q-030, q-041; chưa canonical: q-036 |
| Program efficiency | 1 | 2 | 0 | 3 | approved: q-006, q-019, q-037 |
| Searching | 0 | 3 | 0 | 3 | approved: q-019, q-037, q-038 |
| Sorting | 0 | 1 | 0 | 1 | approved: q-038 |
| Out-of-scope controls | 2 | 3 | 0 | 5 | approved: q-012, q-013, q-042, q-043, q-044 |

## Batch 02 chưa canonical

- Human Answer Points decision `Reject`: q-024, q-028, q-036.

## Quy tắc cập nhật

Mỗi lần thêm, thay wording, chấp nhận hoặc loại một evaluation question, cập nhật hàng concept liên quan, số đếm và Question IDs trong matrix này cùng milestone đó. Chỉ chuyển một câu answerable sang cột approved khi canonical JSONL có record `approved` với Answer Points và source evidence đã được human review. Out-of-scope control được approved với Answer Points và evidence rỗng sau quyết định human review.
