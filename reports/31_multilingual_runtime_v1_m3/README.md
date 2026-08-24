# Multilingual Runtime V1 — M3 Vietnamese End-to-End Evaluation

Status: `preregistered_not_executed`.

Pre-registration revision 2 SHA-256:
`6c127e5e469e019409793e47a9ecfe453221810ad9f8fac794f7f94716920d52`.

Revision 2 được khóa trước execution và trước khi có hoặc quan sát bất kỳ kết quả M3
nào. Revision này chỉ harden phương pháp: bỏ G5 khỏi primary gate, thêm Wilson CI,
randomization, blind self re-review và chính sách abort. G1-G4, matched baseline,
runtime, rubric và negative scope không đổi.

## Research question

> Với runtime đã đóng băng sau M2, câu hỏi tiếng Việt có tạo ra câu trả lời tiếng Việt
> đúng, grounded và có citation hỗ trợ hay không?

M3 đánh giá composite system. Nó không thay đổi kết luận M2: translator
`llama3.2:3b` vẫn FAIL vai trò literal translator và M2 vẫn `frozen_failed`.

## Runtime under test

```text
question_vi
  -> pinned literal translator
  -> retrieval_query
  -> canonical Dense Top 3
  -> G0(original question_vi + English evidence + answer_language=vi)
  -> Vietnamese answer + application-owned citations
```

Không có translation/retrieval/generation tuning, retry, repair, external evidence,
BM25, RRF hoặc reranker.

## Evaluation scope

- Execute đủ 20 paired intents đã freeze.
- Primary evaluation dùng 19 intents.
- `mit60001-q-023` được execute và giữ làm descriptive output nhưng loại khỏi primary
  gate vì canonical Reliability V1 đã freeze exclusion do nguy cơ Ground Truth
  under-credit. M3 không tự sửa exclusion hoặc Ground Truth.
- Bộ này chỉ có answerable questions nên M3 không claim out-of-scope abstention quality.

## Interpretation boundary

M3 có thể chứng minh VI end-to-end không suy giảm quá ngưỡng đã đăng ký so với matched
English baseline. Nó không thể chứng minh runtime nói chung production-ready vì frozen
English G0 Reliability V1 cũng chưa production-ready.

## Pre-registered primary gate

Tất cả G1-G4 phải PASS:

| Gate | Điều kiện |
|---|---|
| G1 Runtime integrity | 20/20 runtime PASS; đúng một translation và một generation call; Top 3; không retry |
| G2 Language compliance | Mọi answer là `Vietnamese` hoặc `Mixed technical terms acceptable`; không có `Not Vietnamese` |
| G3 Decision parity | Ít nhất 10/19 decision đúng; frozen matched English là 11/19 |
| G4 Strict E2E parity | Ít nhất 6/19 strict E2E success; frozen matched English là 7/19 |

Strict answer success yêu cầu đồng thời: evidence sufficient, quyết định answer,
`Correct`, `Complete`, `Grounded`, `All support` và output language compliant. Nếu
evidence insufficient thì strict E2E success yêu cầu abstain.

Strict answer success vẫn được báo cáo nhưng chỉ là diagnostic. Frozen matched English
chỉ đạt 2/19; ở cỡ mẫu 19, ngưỡng cũ `>=2` có xác suất FAIL khoảng 0,390953 ngay cả
khi VI có cùng xác suất thành công nền. Vì vậy số đo này không đủ ổn định để làm
promotion gate.

Mọi proportion chính phải báo numerator, denominator, rate và Wilson CI 95% với
`z=1.959963984540054`. Với 19 primary records, M3 không đủ độ phân giải để kết luận
chắc về chênh lệch nhỏ hơn khoảng 3-4 câu; PASS/FAIL do đúng một câu không được
diễn giải thành parity hoặc inferiority chính xác.

## Human-review controls

Worksheet được sắp xếp bằng SHA-256 của `6000103:<intent_id>`, không theo thứ tự M2.
Reviewer vẫn là người đã review M2, nên nguy cơ anchoring do trí nhớ được ghi nhận là
limitation; giấu nhãn M2 và đổi thứ tự chỉ giảm chứ không xóa được nguy cơ này.

Sau tối thiểu 48 giờ, sáu primary record được chọn trước bằng seed
`6000103-rereview` phải được blind self re-review: `q-022`, `q-016`, `q-020`,
`q-005`, `q-014`, `q-039`. Percent self-agreement theo từng dimension và strict
outcome là diagnostic-only.

## Execution boundary

`--verify-only` kiểm tra 14 frozen inputs, 6 runtime source, runner hash, 20 intent và
matched English baseline; nhánh này return trước encoder load và mọi Ollama call.

Full execution sẽ tạo raw JSONL, worksheet human review có BOM và execution manifest.
Ground Truth/expected answer points chỉ được join sau khi toàn bộ model call hoàn tất;
chúng không đi vào translator, retriever hoặc G0 prompt.

Failure trước model call đầu tiên là infrastructure abort và không tạo result attempt.
Sau khi execution bắt đầu, provider/contract/runtime failure được ghi làm dữ liệu,
làm G1 FAIL và dừng ngay, không retry hay chạy tiếp. Nếu process/máy bị gián đoạn,
partial output được giữ với `aborted_incomplete`; chạy lại cần attempt ID mới và duyệt
rõ, không xóa hay chọn lọc attempt cũ.

Pre-registration và runner phải được verify trước mọi Ollama call. Kết quả live và
human review chưa tồn tại ở trạng thái hiện tại.
