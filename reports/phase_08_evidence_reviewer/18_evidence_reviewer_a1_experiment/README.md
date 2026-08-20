# Phase 8 M2 — A1 two-stage evidence reviewer runtime

## Mục tiêu

M2 triển khai đúng một candidate kiến trúc `A1` với cùng model
`llama3.2:3b`:

```text
Question
   ↓
Stage 1: phân tích các yêu cầu thiết yếu chỉ từ question
   ↓
Stage 2: kiểm tra từng yêu cầu với Dense Top 3
   ↓
Deterministic reducer
   ↓
accept khi và chỉ khi mọi yêu cầu đều supported; ngược lại reject
```

Stage 1 không nhận candidate evidence, Ground Truth, expected answer points,
human labels hoặc previous decisions. Stage 2 không tạo final accept/reject.
Supporting IDs trùng trong cùng một requirement được canonicalize bằng code:
giữ lần xuất hiện đầu tiên, không thêm ID và ghi số lượng đã loại để audit.

## Phạm vi đã khóa

- Development requests: `40`.
- Scope đánh giá M3 sau này: `37`.
- Exclusions giữ nguyên: `q-017`, `q-023`, `q-041`.
- Retrieval: `dense_baseline_v1`, Top 3.
- Không tạo hoặc sử dụng holdout.
- Không sửa Ground Truth và không tạo exclusion mới.
- Không tải model.
- M2 không đọc Ground Truth và không tính quality metrics.

## Runtime

| Thuộc tính | Giá trị |
|---|---|
| Provider | Ollama `0.32.14` |
| Model | `llama3.2:3b` |
| Digest | `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` |
| Quantization | `Q4_K_M` |
| Temperature / seed | `0 / 42` |
| `num_predict` | `512` |
| Context capability | `131072` |
| Context thực dùng | `4096` |
| Processor khi chạy | `20% CPU / 80% GPU` |

Context capability là giới hạn metadata của model; context thực dùng của
experiment là `num_ctx=4096`. Hai giá trị này không được hiểu là một.

## Kết quả runtime và stability

| Run | Questions | Model calls | Accept | Reject | Failures | Duplicate IDs canonicalized |
|---|---:|---:|---:|---:|---:|---:|
| Primary | 40 | 80 | 0 | 40 | 0 | 1 |
| Repeat | 40 | 80 | 0 | 40 | 0 | 1 |

Primary là canonical. Repeat chỉ dùng để kiểm tra stability; không có voting,
best-of hoặc thay thế primary.

| Stability check | Kết quả |
|---|---:|
| Stage 1 exact match | 40/40 |
| Stage 2 exact match | 40/40 |
| Final response exact match | 40/40 |
| Decision changes | 0 |
| Supporting-ID changes | 0 |

Phân bố `0 accept / 40 reject` chỉ là output của runtime. M2 chưa đối chiếu với
canonical human labels, vì vậy không được dùng phân bố này để kết luận model tốt
hay xấu. FAR, accept recall và evidence precision thuộc M3.

## Validation

Validator offline kiểm tra lại:

- schema và 40 question IDs của từng artifact;
- Stage 1 không chứa evidence/evaluation labels;
- Stage 2 không tạo final decision;
- requirement IDs đầy đủ, duy nhất và supporting IDs thuộc Dense Top 3;
- deterministic reducer tái tạo đúng final responses;
- input/output hashes và stability manifest;
- context thực dùng là `4096`;
- `download_performed=false`, `ground_truth_read=false` và holdout không được dùng.

Kết quả: `validation_status=passed`. Toàn bộ test trong
`tests/evidence_review` đạt `40 passed` tại thời điểm validation M2.

## Artifact đã khóa

- Primary/repeat requirement analyses, entailment analyses và final reviews.
- Primary/repeat validation CSV.
- Stability comparison JSON.
- Experiment manifest khóa input/output SHA-256, runtime identity, retrieval
  identity, execution config và operating condition.

## Trạng thái

M2 A1 hoàn thành ở mức runtime:
`complete_runtime_only_not_quality_evaluated`.

M3 chưa chạy. Bước tiếp theo, nếu được duyệt, là join primary canonical output
với canonical human labels trên đúng 37 câu, phân biệt retrieval miss với
reviewer error, tính FAR/accept recall/evidence precision và áp dụng các ngưỡng
đã đăng ký trước. Dù A1 pass hay fail M3, experiment reviewer dừng sau M3 theo
stopping rule đã khóa.
