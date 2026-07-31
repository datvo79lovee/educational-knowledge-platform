# Batch 01 content review

## Ngày review

2026-07-30

## Quyết định của human reviewer

```text
Keep: q-001, q-002, q-003, q-004, q-005, q-006, q-007, q-008,
      q-009, q-010, q-014
Rewrite: q-011
Rewrite for source-grounded retrieval: q-001, q-005, q-006, q-009
Keep out-of-scope: q-012, q-013
Rejected: none
```

Q-011 được đổi thành:

```text
How does the course compare recursion and iteration for solving problems?
```

## Source-grounded rewrites ngày 2026-07-31

Các câu dưới đây được đổi để yêu cầu evidence từ course/lecture thay vì khuyến
khích trả lời từ kiến thức Python chung:

| Question ID | English question | Vietnamese query draft |
| --- | --- | --- |
| `mit60001-q-001` | According to the course introduction, what learning goals are introduced for students? | Theo phần giới thiệu khóa học, những mục tiêu học tập nào được giới thiệu cho sinh viên? |
| `mit60001-q-005` | According to the course, why does a recursive function require a base case? | Theo khóa học, tại sao hàm đệ quy cần có điều kiện dừng (base case)? |
| `mit60001-q-006` | According to the lecture, how is the efficiency of an algorithm explained? | Theo bài giảng, hiệu quả của một thuật toán được giải thích như thế nào? |
| `mit60001-q-009` | According to the course, how are local variables created and used during a function call? | Theo khóa học, biến cục bộ được tạo và sử dụng như thế nào trong lời gọi hàm? |

Vietnamese query drafts chỉ là wording để chuẩn bị cho retrieval đa ngôn ngữ;
chúng chưa được thêm vào canonical evaluation dataset và chưa có evidence được
chấp nhận.

## Ý nghĩa trạng thái

Review này chỉ xác nhận câu hỏi phù hợp về nội dung dự kiến. Các record vẫn là
`draft`: chưa có expected answer points, video ID hoặc timestamp evidence. Không
được dùng batch này để tính retrieval metrics cho đến khi source review hoàn tất.

Source candidate locator sẽ tạo `batch_01_source_candidates_with_transcript.csv`. Đây chỉ là danh
sách đoạn cần đọc, không phải citation hoặc evidence đã được chấp nhận. File có
`start_transcript_text`, `end_transcript_text` và `transcript_excerpt` đúng theo
source segment range/timestamp để human reviewer đọc context. Vì có raw transcript
excerpt, file này là review artifact; không được đặt trong folder `reports/`.

## Quyết định source review ngày 2026-07-31

Nguồn quyết định: `C:\Users\MSI\Downloads\batch_01_review_vi_with_decision.xlsx`.
Quyết định dưới đây tách question-level action khỏi candidate-level relevance.

| Question ID | Question decision | Hành động |
| --- | --- | --- |
| `mit60001-q-001` | `accept` | Tạo candidate ground-truth draft từ candidate được human review là chính xác. |
| `mit60001-q-002` | `accept` | Tạo candidate ground-truth draft từ candidate được human review là chính xác. |
| `mit60001-q-003` | `rewrite` | Đổi wording sang scope/variable names, sau đó tạo source candidates mới. |
| `mit60001-q-004` | `rewrite` | Đổi wording để phân biệt `=` và `==`, sau đó tạo source candidates mới. |
| `mit60001-q-005` | `needs_more_evidence` | Giữ wording, tìm candidate mới về base case. |
| `mit60001-q-006` | `accept` | Tạo candidate ground-truth draft. |
| `mit60001-q-007` | `accept` | Tạo candidate ground-truth draft. |
| `mit60001-q-008` | `accept` | Tạo candidate ground-truth draft. |
| `mit60001-q-009` | `accept` | Tạo candidate ground-truth draft. |
| `mit60001-q-010` | `accept` | Tạo candidate ground-truth draft. |
| `mit60001-q-011` | `needs_more_evidence` | Giữ intent so sánh recursion/iteration, tìm candidate mới có evidence so sánh. |
| `mit60001-q-012` | `out_of_scope` | Giữ `answerable=false`; không gắn corpus evidence. |
| `mit60001-q-013` | `out_of_scope` | Giữ `answerable=false`; không gắn corpus evidence. |
| `mit60001-q-014` | `accept` | Tạo candidate ground-truth draft. |

`accept` ở bảng này cho phép tạo candidate ground-truth draft, không tự đặt
`review_status=approved` trong canonical evaluation dataset. Canonical approval vẫn
cần expected answer points, video/time range cuối cùng và human final check theo
evaluation contract.

## Candidate file hiện hành sau quyết định

File candidate hiện hành cho review tiếp theo là
`evaluation/review/batch_01_source_candidates_with_transcript_2026-07-31_v2.csv`.
Nó được tạo lại từ draft sau khi rewrite q-003 và q-004; file
`batch_01_source_candidates_with_transcript_2026-07-31.csv` được giữ nguyên để
audit và không dùng để review wording mới của hai câu đó.

q-005 và q-011 có thêm source expansion thủ công trong
`BATCH_01_ADDITIONAL_EVIDENCE_CANDIDATES.md`; các đoạn này vẫn là candidate, chờ
human source review.

## Canonicalization milestone

`evaluation/mit_60001/evaluation_questions.jsonl` hiện có 13 record Batch 01 được
human final approve: 11 câu answerable và q-012/q-013 out-of-scope. q-003 dùng v2
rank 1; q-004 dùng v2 rank 3; q-005 dùng additional source expansion segments
105–116. q-011 vẫn chưa có canonical record vì cần evidence so sánh rõ hơn.

Subset này vẫn chưa đủ 40–60 câu để chạy retrieval comparison hoặc lựa chọn full Gold
configuration.
