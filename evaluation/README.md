# Evaluation question review workflow

## Vai trò file

- `templates/mit_60001_evaluation_questions_template.csv`: file để nhập và review.
- `drafts/`: candidate chưa kiểm source; không dùng cho evaluation.
- `mit_60001/evaluation_questions.jsonl`: canonical dataset đã parse và validate.
  Hiện có 13 record `approved` của Batch 01 (11 answerable, 2 out-of-scope);
  chỉ record `approved` được dùng để chọn chunking configuration hoặc tính retrieval
  metrics.

CSV không phải JSON Schema input trực tiếp. Các cột array phải chứa JSON compact
trong cell, như quy định tại `docs/design/CHUNKING_EVALUATION_CONTRACT.md`.

## Checklist trước khi chuyển một câu thành approved

1. `question_id` chưa xuất hiện trong dataset.
2. Question là tiếng Anh và thuộc đúng category.
3. Với answerable question: đọc source, ghi expected answer points, relevant video ID
   và exact time range; không dùng title hoặc kiến thức Python chung làm evidence.
4. Với out-of-scope question: `answerable=false` và ba field evidence là `[]`.
5. Reviewer thay `unassigned` bằng định danh người review và ghi review notes.
6. Kiểm tra `end_second > start_second`, video ID khớp giữa time range và evidence list.
7. Chỉ sau bảy bước trên mới đặt `review_status=approved`.

LLM evidence review là bước hỗ trợ sau retrieval, không thay thế checklist này. Nó chỉ
trả `accept` hoặc `reject`; Answer Points do LLM tạo chỉ là candidate và chỉ được tạo
sau `accept`. Xem `docs/design/RETRIEVAL_EVIDENCE_REVIEW_CONTRACT.md`.

## Trạng thái review

```text
draft     : candidate chưa được kiểm source
reviewed  : đã kiểm một phần nhưng chưa đủ evidence
approved  : đủ evidence, được phép dùng evaluation
rejected  : không phù hợp hoặc không có evidence rõ
```

Không dùng `draft` hoặc `reviewed` để chọn chunking configuration.
