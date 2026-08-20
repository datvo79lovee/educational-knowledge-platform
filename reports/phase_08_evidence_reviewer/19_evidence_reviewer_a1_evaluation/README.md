# Phase 8 M3 — A1 canonical evaluation

## Mục tiêu

M3 join primary output đã khóa của A1 với 37 canonical human decision labels,
tính decision metrics, xác nhận final selected supporting pairs và áp dụng các
quality thresholds đã đăng ký trước.

M3 không gọi model, không sửa prompt/model/Ground Truth, không tạo exclusion
mới và không tạo human-review workbook khi không có final selected pair.

## Scope đã khóa

- Development questions: `40`.
- Evaluable questions: `37`.
- Canonical expected accept: `21`.
- Canonical expected reject: `16`.
- Exclusions giữ nguyên: `q-017`, `q-023`, `q-041`.
- A1 primary predictions trên 37-scope: `0 accept`, `37 reject`.

## Decision metrics

| Metric | A1 |
|---|---:|
| TP | 0 |
| FP | 0 |
| FN | 21 |
| TN | 16 |
| Accuracy | 43.24% |
| Accept precision | N/A — không có predicted accept |
| Accept recall | 0% |
| False accept rate | 0% |
| False reject rate | 100% |

FAR `0%` không được diễn giải là một reviewer hữu ích hoặc an toàn. A1 đã
collapse về một class: mọi câu trong evaluation scope đều bị reject.

## Evidence-selection metric

Final A1 responses không chọn supporting chunk nào trên 37-scope:

```text
selected final question–chunk pairs = 0
evidence precision = 0 / 0 = undefined
```

Vì vậy evidence precision được ghi `null` / `N/A` với trạng thái
`not_evaluable_zero_selected_pairs`. Metric này không được ghi `100%` và không
được đánh dấu PASS.

## Stage 2 internal audit

| Internal value | Count |
|---|---:|
| Questions | 40 |
| Requirement assessments | 103 |
| Supported requirements | 21 |
| Unsupported requirements | 82 |
| Questions có ít nhất một supported requirement | 20 |
| Questions có toàn bộ requirements supported | 0 |

Requirement-level supporting IDs chỉ dùng để debug kiến trúc. Chúng không phải
final selected question–chunk pairs và không được đưa vào evidence precision.

## Frozen quality gate

| Gate | Result | Threshold | Status |
|---|---:|---:|---|
| Runtime/schema | Valid | Contract | PASS |
| Accept recall | 0% | >= 75% | **FAIL** |
| FAR | 0% | <= 25% | PASS |
| Evidence precision | N/A, 0 selected pairs | >= 85% | **NOT EVALUABLE** |
| Overall |  |  | **failed_candidate** |

Candidate fail do accept recall thấp hơn threshold. Evidence precision không
evaluable không bị biến thành PASS.

## Validation và freeze

- Canonical scope được xác nhận đúng `21 accept + 16 reject + 3 exclusions`.
- Confusion matrix được tái tạo từ từng dòng decision result.
- Primary A1 source hashes được đối chiếu với M2 manifest.
- Input/output SHA-256 và evaluation run identity được khóa trong final
  manifest.
- Validator offline PASS.
- Toàn bộ `tests/evidence_review` đạt `45 passed` tại thời điểm freeze.
- Model calls trong M3: `0`.
- Human-review workbook được tạo: `false`.

## Kết luận

A1 là `failed_candidate`. Kết luận khoa học được giới hạn ở mức: không cấu hình
Evidence Reviewer nào đã thử đạt toàn bộ frozen quality thresholds. Không kết
luận model intrinsically incapable và không claim generalization.

Evidence Reviewer research dừng sau A1 theo stopping rule đã khóa. Reviewer hiện
chỉ có thể được mô tả là `experimental evidence gate — quality threshold not
achieved`.

Determinism không đồng nghĩa với quality: A1 đạt exact match `40/40` giữa
primary/repeat nhưng vẫn fail quality gate do reject collapse.

Bước tiếp theo là M4 đồng bộ documentation, sau đó chuyển sang Grounded Answer
Generator mà không giả định Evidence Reviewer hiện tại production-ready.
