# Multilingual Runtime V1 — M3 Vietnamese End-to-End Evaluation

Status: `frozen_failed_runtime_integrity` — attempt 1 dừng ở runtime integrity.

```text
Multilingual Runtime V1 — M3 attempt 1
G1 runtime integrity : FAIL   1 runtime failure tại mit60001-q-002
G2 language          : NOT_EVALUATED
G3 decision parity   : NOT_EVALUATED
G4 strict E2E parity : NOT_EVALUATED
Overall              : FAIL
Executed             : 2/20 intents (1 passed, 1 failed, 18 không chạy)
Retries              : 0
```

**Không có kết luận nào về chất lượng end-to-end tiếng Việt.** G2–G4 không có dữ
liệu; chúng không được báo cáo là passed, failed hay ước lượng. Chi tiết freeze nằm
tại `m3_final_manifest.json`.

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

Pre-registration và runner phải được verify trước mọi Ollama call.

## Attempt 1 — điều đã xảy ra

Attempt `m3-attempt-1` chạy `q-001` thành công rồi dừng ở `q-002`. Generator trả
`decision="abstain"` kèm answer khác null; strict contract từ chối output đó với
`GroundedAnswerContractError` ("abstain decision requires answer=null"). Runner ghi
record rồi dừng ngay, đúng `runtime_failure_policy`, không retry.

Đây là **vi phạm contract ở tầng generation**. Nó không phải bằng chứng translator
hay retrieval sai trên intent đó.

Hai quan sát được ghi lại, không phải kết luận:

- Biến thể lỗi này **không xuất hiện** trong frozen English Reliability V1: 40/40
  public success, 0 public failure, và normalization chỉ gặp `abstain_literal_to_null`
  cùng `duplicate_supporting_ids`. Với 2 record tiếng Việt thì đây là một quan sát,
  không phải một tỉ lệ và không phải quan hệ nhân quả.
- `q-001` retrieve bằng `retrieval_query = "Learning Objectives"`, đúng output mà M2
  đã gán `Semantic drift`. Runtime vẫn sinh câu trả lời kèm citation mà không phát
  hiện query của mình đã hỏng.

### Diagnostic capture limitation

Record failed **không giữ** dữ liệu cần để phân tích: `retrieval_query` là `null`,
`top3_chunk_ids` rỗng, `raw_model_output` không có — dù một translation call đã hoàn
tất cho intent đó (`translation_call_count: 1`, `459 ms`). Thông điệp lỗi Pydantic
cũng cắt ngắn output vi phạm.

Hệ quả: bản dịch, evidence và toàn văn output của generator cho `mit60001-q-002`
**không khôi phục được** từ artifact attempt 1. Đây là lỗ hổng capture của runner trên
error path, không phải vi phạm protocol và không phải defect của runtime. Việc khắc
phục thuộc một milestone sau có pre-registration riêng; attempt 1 không được chạy lại
để lấy lại dữ liệu đó.

### Ranh giới của freeze

Freeze chỉ ghi nhận kết quả đã có. Không rerun, không xóa hay thay thế attempt 1,
không sửa artifact hay hash nào của attempt 1, không tính quality metric, không human
review, và không đụng runtime, prompt, model, retriever hay normalization.

Không mở rộng normalization để tự chuyển `abstain` + answer khác null thành
`answer=null`. Hai rule normalization hiện có chỉ canonicalize nhiễu biểu diễn; rule
đó sẽ **vứt bỏ output của model** và tự quyết định `decision` đáng tin hơn `answer` —
đó là phán đoán ngữ nghĩa, không phải canonicalization.

### Bước tiếp theo

Chưa chuẩn bị. Attempt 2 chưa được chạy và runtime chưa được sửa. Bài học về dụng cụ
đo: stop-on-first-failure là gate đúng cho hệ thống được tin là toàn vẹn, nhưng nó
triệt tiêu năng lực đo với hệ thống có tỉ lệ lỗi chưa biết — 20 intents đã thành 2
record.
