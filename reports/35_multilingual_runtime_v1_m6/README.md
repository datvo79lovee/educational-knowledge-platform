# Multilingual Runtime V1 — M6 quality evaluation

## Trạng thái

`FROZEN — PASSED QUALITY GATES G1–G4`

M6 đã đóng băng tại `m6_final_manifest.json`. Kết luận được phép duy nhất:

> The frozen M5.3 Vietnamese candidate passed M6 quality gates on the 19-record
> primary reused evaluation sample.

Không được suy ra: production-ready, tổng quát hóa sang query chưa thấy, quan hệ nhân
quả giữa translation/retrieval/generation và lỗi cuối, translator fidelity đã phục
hồi, hay M2 (literal translator, `frozen_failed`) bị đảo ngược/hủy bỏ. M6 không mở lại
M2.

## Câu hỏi nghiên cứu

Trên đúng sample 20 intent đã freeze, nhánh VI có tạo answer/abstention đạt rubric
đã đăng ký trước về decision, ngôn ngữ, correctness, completeness, groundedness và
citation support hay không?

## Scope và baseline

- Worksheet: 20 intent.
- Primary: 19 intent.
- `mit60001-q-023`: review mô tả nhưng loại khỏi primary metric do Ground Truth
  ambiguity đã freeze từ Reliability V1.
- Matched English reference: decision correct 11/19; strict E2E 7/19; strict answer
  2/19 (diagnostic only).

## Gate — kết quả cuối (từ `m6_evaluation_manifest.json`, khóa lại tại freeze)

| Gate | Điều kiện | Quan sát | Kết quả |
|---|---|---:|---|
| G1 review integrity | 20/20 reviewed, 19 primary, 1 excluded, nhãn hợp lệ | 20/19/1 | PASS |
| G2 language compliance | mọi answer primary phải Vietnamese/Mixed acceptable | 12/12 | PASS |
| G3 decision non-inferiority | ≥10/19 | 14/19 | PASS |
| G4 strict E2E non-inferiority | ≥6/19 | 7/19 | PASS |

G1–G4 đều PASS. Strict answer success (1/19, Wilson 95% [0,009; 0,246]) vẫn chỉ là
diagnostic vì English reference 2/19 quá thấp để làm gate ổn định.

Tỉ lệ đầy đủ kèm Wilson 95%, đọc từ `m6_metrics.json`:

```
decision_correct              14/19 = 0,7368   CI [0,5121; 0,8819]
language_compliance            12/12 = 1,0000   CI [0,7575; 1,0000]
strict_end_to_end_success       7/19 = 0,3684   CI [0,1915; 0,5896]
strict_answer_success (diag)    1/19 = 0,0526   CI [0,0094; 0,2464]
```

## Blind review

Worksheet chính chỉ hiển thị câu hỏi VI, expected answer points, Top-3 evidence,
decision, final answer và các excerpt citation được ứng dụng chọn. Nó cố ý không hiển
thị `retrieval_query`, raw translation/model output, normalization metadata, nhãn M2
hoặc quality outcome cũ. Diagnostic sau review (`retrieval_query`, Top-3, cờ
normalization cho các intent thất bại strict E2E) chỉ được join **sau khi** toàn bộ
nhãn review hợp lệ, và chỉ mang tính quan sát — không gán nguyên nhân.

Đây vẫn là single-reviewer evaluation trên sample đã dùng nhiều lần. Randomization và
ẩn diagnostic không loại bỏ được memory anchoring; M6 không đo inter-annotator hay
delayed intra-annotator agreement.

## Freeze

```powershell
python -X utf8 scripts/evaluation/freeze_multilingual_runtime_v1_m6.py
```

Script chỉ re-hash sáu artifact M6-E, đối chiếu với `m6_evaluation_manifest.json`, và
ghi `m6_final_manifest.json`. Không gọi Ollama, không rerun `--evaluate`, không sửa
nhãn review, result artifact, M5.3, runtime, prompt, normalization hay
Dense/index/Gold/Ground Truth. Re-runnable: nếu `m6_final_manifest.json` đã tồn tại,
script raise `FileExistsError` thay vì ghi đè.

## Ranh giới diễn giải (khóa tại freeze)

PASS chỉ cho phép cân nhắc chuyển candidate không đổi sang một milestone demo cục bộ
có giới hạn, scope riêng. Nó không chứng minh production readiness, chất lượng trên
query chưa thấy, hay quan hệ nhân quả giữa translation/retrieval/generation và lỗi
cuối. Với n=19, một record tương đương 5,26 điểm phần trăm; kết quả sát ngưỡng không
phải bằng chứng parity chính xác. Đây là một lượt review bởi một người, không đo được
inter-annotator hay delayed intra-annotator agreement.
