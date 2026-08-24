# Multilingual Runtime V1 — M6 quality evaluation

## Trạng thái

`PREPARED FOR BLIND HUMAN REVIEW — NO QUALITY RESULT YET`

M6 chỉ đánh giá 20 output tiếng Việt đã freeze tại M5.3. M6 không gọi Ollama,
không chạy lại retrieval, không sửa runtime, prompt, normalization, Gold hoặc Ground
Truth. Cho tới khi worksheet được review đầy đủ và evaluator chạy, không có kết luận
về correctness, groundedness, citation support, parity hoặc demo readiness.

## Câu hỏi nghiên cứu

Trên đúng sample 20 intent đã freeze, nhánh VI có tạo answer/abstention đạt rubric
đã đăng ký trước về decision, ngôn ngữ, correctness, completeness, groundedness và
citation support hay không?

## Scope và baseline

- Worksheet: 20 intent.
- Primary: 19 intent.
- `mit60001-q-023`: vẫn review và giữ descriptive, nhưng loại khỏi primary metric do
  Ground Truth ambiguity đã freeze từ Reliability V1.
- Matched English reference: decision correct 11/19; strict E2E 7/19; strict answer
  2/19 (diagnostic only).

## Gate đã khóa trước review

- G1: review integrity PASS.
- G2: mọi answer thuộc primary scope phải là Vietnamese hoặc Mixed technical terms
  acceptable.
- G3: decision correct ít nhất 10/19.
- G4: strict E2E ít nhất 6/19.

G1–G4 phải cùng PASS. Strict answer success chỉ là diagnostic vì English reference
2/19 quá thấp để làm gate ổn định.

## Blind review

Worksheet chính chỉ hiển thị câu hỏi VI, expected answer points, Top-3 evidence,
decision, final answer và các excerpt citation được ứng dụng chọn. Nó cố ý không hiển
thị `retrieval_query`, raw translation/model output, normalization metadata, nhãn M2
hoặc quality outcome cũ. Các diagnostic này chỉ được join sau khi toàn bộ nhãn review
đã hợp lệ.

Đây vẫn là single-reviewer evaluation trên sample đã dùng nhiều lần. Randomization và
ẩn diagnostic không loại bỏ được memory anchoring; M6 không đo inter-annotator hay
delayed intra-annotator agreement.

## Cách dùng

Chỉ verify, không ghi file:

```powershell
python scripts/evaluation/run_multilingual_runtime_v1_m6.py --verify-only
```

Sinh worksheet review mù (chỉ chạy một lần trong preparation milestone):

```powershell
python scripts/evaluation/run_multilingual_runtime_v1_m6.py --prepare
```

Sau khi human review, lưu bản review thành
`m6_human_review_worksheet_reviewed.csv`. Không chạy `--evaluate` trước khi artifact
review được user xác nhận và milestone evaluation được duyệt riêng.

## Ranh giới diễn giải

Ngay cả khi PASS, M6 chỉ cho phép cân nhắc milestone demo cục bộ có giới hạn. Nó không
chứng minh production readiness, chất lượng trên query chưa thấy, hay quan hệ nhân quả
giữa translation/retrieval/generation và lỗi cuối. Với n=19, một record tương đương
5,26 điểm phần trăm; kết quả sát ngưỡng không phải bằng chứng parity chính xác.
