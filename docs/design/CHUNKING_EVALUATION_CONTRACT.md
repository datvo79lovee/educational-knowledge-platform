# Chunking evaluation contract v1

## Trạng thái

Đã chốt template và review rules ngày 2026-07-27. Dataset câu hỏi hiện là template trống; chưa có question nào được chấp nhận làm ground truth.

## Mục tiêu

Evaluation chọn configuration chunking bằng retrieval evidence, không đánh giá câu trả lời nghe có vẻ hay. Dataset chỉ áp dụng cho MIT 6.0001 target scope.

```text
schema_version: chunking_evaluation_question_v1
scope_version: mit_60001_fall_2016_v1
target question count: 40–60
```

## Field của một evaluation question

| Field | Quy tắc |
| --- | --- |
| `question_id` | Bất biến, ví dụ `mit60001-q-001` |
| `scope_version` | `mit_60001_fall_2016_v1` |
| `question` | Câu hỏi tiếng Anh dùng để retrieval trong corpus English |
| `category` | factual, concept, code, multi-chunk, confusable, hoặc out-of-scope |
| `answerable` | Có thể trả lời chỉ bằng corpus hay không |
| `expected_answer_points` | Điểm ý cần chứng minh, không phải câu trả lời dài |
| `relevant_video_ids` | Video chứa evidence |
| `relevant_time_ranges` | Citation range do người review kiểm từ nguồn |
| `review_status` | draft, reviewed, approved hoặc rejected |
| `reviewer`, `review_notes` | Người review và lý do/ambiguity |

## Quy tắc authoring và review

1. Câu hỏi do AI đề xuất chỉ có trạng thái `draft`.
2. Chỉ câu hỏi được người hiểu Python chuyển `approved` mới được dùng để chọn configuration hoặc kết luận Recall@k/citation.
3. Expected answer points, video ID và time range phải được kiểm từ nguồn; không suy ra chỉ từ title hoặc kiến thức Python chung.
4. `out_of_scope` có `answerable=false` và không có video/time range. Nó chỉ dùng đánh giá abstention ở phase sau, không dùng tính chunk Recall@k.
5. Một câu hỏi answerable có thể có nhiều video/range khi evidence thực sự nằm ở nhiều đoạn. Không dùng một LLM khác làm judge duy nhất.

## Phân bố mục tiêu

| Category | Số mục tiêu |
| --- | ---: |
| factual | 8–12 |
| concept_explanation | 10–14 |
| code_behavior | 10–14 |
| multi_chunk | 5–8 |
| confusable | 5–8 |
| out_of_scope | 5–8 |

Tổng phải nằm trong 40–60. Phân bố không phải lý do chấp nhận câu hỏi kém chất lượng.

## Cách dùng cho chunking experiment

Chỉ lọc câu hỏi `approved` và `answerable=true`. Với từng question/configuration, ghi top-k chunk ID, rank của chunk relevant đầu tiên, video/time citation và manual judgment. So sánh Recall@k, MRR, citation correctness và số chunk cần đọc. Không dùng answer generation trong milestone chunking.

## Output

```text
schemas/chunking_evaluation_question_v1.schema.json
evaluation/templates/mit_60001_evaluation_questions_template.csv
```

Template CSV không có transcript text, Gold chunk text hoặc câu hỏi giả.
