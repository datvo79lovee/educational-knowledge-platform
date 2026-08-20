# Phase 8 M3 — Prompt experiment evaluation

## Phạm vi đã khóa

M3 đánh giá ba run trên cùng 37 canonical human decision labels:

```text
E0  locked baseline
E1  current-runtime prompt V1 control
E2  prompt V2 candidate
```

Ba câu `q-017`, `q-023`, `q-041` giữ nguyên exclusion của baseline. Không tạo
exclusion mới, không sửa prompt/model, không tải model và không sửa Ground Truth.

## Decision metrics — 37 câu

| Run | TP / FP / FN / TN | Accuracy | Accept precision | Accept recall | FAR | FRR |
|---|---|---:|---:|---:|---:|---:|
| E0 | 17 / 9 / 4 / 7 | 64.86% | 65.38% | 80.95% | 56.25% | 19.05% |
| E1 | 16 / 9 / 5 / 7 | 62.16% | 64.00% | 76.19% | 56.25% | 23.81% |
| E2 | 19 / 9 / 2 / 7 | 70.27% | 67.86% | 90.48% | 56.25% | 9.52% |

E2 tăng recall nhưng không giảm false accept. Với ngưỡng đăng ký trước
`FAR <= 25%`, E2 đã fail decision gate ở `56.25%`.

## Audit sáu decision deltas

- `q-001`: E1 đúng (`TN`) → E2 sai (`FP`).
- `q-009`: E1 sai (`FN`) → E2 đúng (`TP`).
- `q-014`: E1 sai (`FP`) → E2 đúng (`TN`).
- `q-019`: E1 sai (`FN`) → E2 đúng (`TP`).
- `q-021`: E1 sai (`FN`) → E2 đúng (`TP`).
- `q-023`: giữ exclusion cũ, chỉ audit; không ép nhãn.

## Evidence-selection audit

| Run | 37-scope selected pairs | Canonical supports | Canonical does-not-support | Pending | Precision hiện có |
|---|---:|---:|---:|---:|---:|
| E0 | 34 | 27 | 7 | 0 | 79.41% |
| E1 | 33 | 26 | 7 | 0 | 78.79% |
| E2 | 67 | 46 | 21 | 0 | 68.66% |

Trên toàn bộ 40 câu, E2 có 70 selected pairs: 48 `supports`, 22
`does_not_support`, evidence precision `68.57%`. Hai cặp thuộc q-023 vẫn được
audit nhưng không đưa vào evidence gate 37-câu.

Union E1/E2 có 73 cặp duy nhất: 35 verdict canonical được tái sử dụng và 38 cặp
đã được human review. Trong 38 cặp mới, reviewer chọn 22 `supports` và 16
`does_not_support`; không có `needs_discussion`.

## Kết quả pre-registered gate

| Ngưỡng | E2 | Yêu cầu | Kết quả |
|---|---:|---:|---|
| Response schema valid rate | 100% | >= 100% | PASS |
| Outside-Top-3 supporting IDs | 0 | <= 0 | PASS |
| Ground Truth leakage | 0 | <= 0 | PASS |
| Accept recall | 90.48% | >= 75% | PASS |
| False accept rate | 56.25% | <= 25% | **FAIL** |
| Evidence-selection precision, 37-scope | 68.66% | >= 85% | **FAIL** |

Rule đã đăng ký trước yêu cầu mọi threshold cùng pass. E2 fail ở false accept
rate và evidence-selection precision, nên kết quả cuối là `failed_candidate`.

## Artifact đã khóa

- Workbook reviewed được giữ nguyên trong project và được nhận diện bằng SHA-256.
- 38 verdict mới được canonicalize riêng; các cột đầu vào bất biến được đối
  chiếu với pending package trước khi nhận nhãn human.
- Audit 73 cặp E1/E2 đã có verdict đầy đủ; không còn pending hoặc
  `needs_discussion`.
- Final manifest khóa hash input/output, metric, threshold result và experiment
  identity.

## Trạng thái

M3 hoàn thành và được freeze với trạng thái `failed_candidate`. Kết luận này chỉ
áp dụng cho candidate E2 trong experiment in-sample hiện tại; không có claim
production-ready hoặc generalization. Prompt V2, model, Ground Truth và tập ba
exclusion cũ không bị sửa trong M3.
