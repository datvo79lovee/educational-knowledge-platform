# Phase 8 M3 — Evidence reviewer evaluation

M3 đánh giá locked output của runtime
`mit60001_evidence_reviewer_0ee5e6a1362fc5c4`. Không có inference mới,
không sửa prompt/model và không sửa Ground Truth.

## Decision correctness — strict baseline trước human review

| Metric | Kết quả |
|---|---:|
| TP / FP / FN / TN | 13 / 7 / 3 / 5 |
| Accuracy | 64.29% |
| Accept precision | 65.00% |
| Accept recall | 81.25% |
| False Accept Rate | 58.33% |
| False Reject Rate | 18.75% |

Các metric này chỉ dùng 16 `strong_accept` và 12 `strong_reject`. Mười hai câu
`needs_human_review` chưa được đưa vào confusion matrix.

False Accept Rate hiện cao: 7/12 strict expected-reject rows bị model accept.
Đây là baseline cần giữ nguyên để đánh giá trước khi mở experiment sửa prompt
hoặc đổi model.

## Evidence selection

Model accept 27 câu và chọn tổng cộng 35 supporting chunks. Trong số này có 19
chunk overlap ít nhất một Ground Truth time range. Overlap chỉ là tín hiệu audit
theo timestamp; nó không chứng minh chunk thực sự entail expected answer points.
Vì vậy 35 supporting chunks vẫn chờ human entailment review.

## Human review còn thiếu

- Sheet `Human Review 12`: phân loại 10 câu partial cùng q-023/q-041.
- Sheet `Evidence Audit`: xác nhận từng supporting chunk là evidence thật hay
  chỉ cùng chủ đề.
- q-023 và q-041 giữ `possible_ground_truth_under_credit`; không sửa benchmark
  trong M3.

## Kết quả cuối sau human review

Human review hoàn thành 12/12 câu và 35/35 supporting chunks. Chín câu bổ sung
đủ điều kiện đưa vào confusion matrix; ba câu được giữ ngoài metric thay vì ép
nhãn:

- q-017: `needs_discussion`.
- q-023 và q-041: `benchmark_gt_issue`, giữ cờ Ground Truth under-credit.

Metric cuối trên 37 câu evaluable:

| Metric | Kết quả |
|---|---:|
| TP / FP / FN / TN | 17 / 9 / 4 / 7 |
| Accuracy | 64.86% |
| Accept precision | 65.38% |
| Accept recall | 80.95% |
| False Accept Rate | 56.25% |
| False Reject Rate | 19.05% |

Evidence selection: 27/35 supporting chunks được human xác nhận `supports`,
tương đương 77.14%; 8/35 là `does_not_support`.

M3 hoàn tất với trạng thái `complete_with_exclusions`. Ground Truth, prompt và
model không bị sửa trong milestone này.
