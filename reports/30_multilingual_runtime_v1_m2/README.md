# Multilingual Runtime V1 — M2: machine translation fidelity

## Trạng thái

```text
Multilingual Runtime V1 — M2
G1 semantic fidelity : FAIL   Semantic drift = 10/20, threshold = 0
G2 retrieval quality : FAIL   Recall@3 = 0,55, threshold = 0,65
Determinism          : FAIL   q-001 khác nhau giữa run A và run B
Overall              : FAILED
VI runtime candidate : REJECTED
```

M2 đã đóng và freeze ở trạng thái `frozen_failed`. Nhánh VI runtime **không được chấp
nhận** để đưa vào demo hay tài liệu năng lực. Không có phương án khắc phục nào được mở
trong milestone này.

Execution attempt 1 đã chạy 40 translator calls nhưng dừng trước metric/output vì
runner truyền Ground Truth ranges chưa resolve vào frozen `branch_metrics`, gây
`KeyError: 'range_index'`. Không có formal result nào được tạo. Sự cố và ràng buộc
repair được lưu tại `m2_execution_attempt_1_failure.json`. Kết quả dưới đây thuộc
execution attempt 2.

## Vì sao cần M2

Phase 9 đo retrieval trên `literal_en` **do người duyệt**. Runtime V1 lại dịch bằng
`llama3.2:3b`. Không có bằng chứng nào cho thấy translator máy giữ được cùng mức
fidelity, nên **kết quả Phase 9 không tự động chuyển sang runtime**. M2 đo đúng cái
đã được ship, không mở research mới.

## Ghi chú đặt tên

Phase 9 đã dùng `m1`/`m2`/`m3` cho **benchmark** multilingual. Milestone này là
Multilingual Runtime V1 M2 và dùng tiền tố riêng `multilingual_runtime_v1_m2` cho mọi
script, report và artifact để không đụng tên với artifact Phase 9 đã freeze.

## Gate đăng ký trước

Cả hai điều kiện phải đồng thời đúng:

| ID | Điều kiện | Ngưỡng | Quan sát | Kết quả |
|---|---|---|---:|---|
| G1 | `Semantic drift` theo rubric M1 | đúng `0` | `10` | **FAIL** |
| G2 | Recall@3 của `machine_literal_en` so với frozen `literal_en` (0,70) | `>= 0,65` | `0,55` | **FAIL** |

Dự đoán đăng ký trước **P1**: `mit60001-q-008` tiếp tục là intent nhạy nhất với
translation, thao tác hóa thành: nó xếp tệ nhất ở ít nhất một trong hai chỉ số —
mức tụt first-relevant-rank lớn nhất, hoặc Top-3 overlap thấp nhất.

## Kết quả

### Bảng ba nhánh

Hai nhánh frozen tái lập **chính xác** baseline Phase 9 (`frozen_baseline_reproduced:
true`), nên chênh lệch quan sát được là thật chứ không do lệch định nghĩa metric.

| Nhánh | MRR | Recall@1 | Recall@3 | Recall@5 | Full Evidence@3 |
|---|---:|---:|---:|---:|---:|
| `question_en` | 0,596 | 0,40 | 0,75 | 0,80 | 0,50 |
| `literal_en` (người duyệt, frozen) | 0,634 | 0,55 | 0,70 | 0,75 | 0,55 |
| `machine_literal_en` | 0,497 | 0,40 | **0,55** | 0,65 | 0,40 |
| Δ machine − frozen | −0,137 | −0,15 | **−0,15** | −0,10 | −0,15 |

Tụt đồng loạt trên mọi metric. Chỉ `1/20` bản dịch máy trùng tuyệt đối với bản dịch
người; mean Top-3 overlap `0,617`.

### Human adjudication

| Nhãn | Số câu |
|---|---:|
| Equivalent | 4 |
| Minor wording difference | 6 |
| **Semantic drift** | **10** |

Worksheet đã review được hash nguyên byte kể cả BOM tại `m2_manifest.json`. Script
freeze kiểm tra chuỗi `machine_literal_en` trong worksheet khớp đúng output đã thực
thi, nên review không thể là bản sao cũ.

### Bốn dạng hỏng

| Dạng | Câu | Ví dụ output |
|---|---|---|
| Xuất nhãn thay vì dịch | q-001, q-010, q-014, q-016, q-037, q-039 | `"List"`, `"Assertion"`, `"Linear search"` |
| Trả lời thay vì dịch | q-022, q-034 | tự sinh cả đoạn giải thích testing/debugging |
| Đảo nghĩa | q-008 | hỏi ngược lại mệnh đề gốc |
| Sai thuật ngữ chuyên ngành | q-033 | `decomposition` → `nuclear fission` |

`num_predict_cap_hits = 0`: **không câu nào bị cắt cụt**. Giả thuyết "chạm trần 128
token" bị dữ liệu bác bỏ; model tự chọn xuất cụm ngắn. Latency dịch trung bình
`596 ms`, tối đa `4 022 ms`.

## Phát hiện chính: retrieval metric có thể mù trước semantic translation failure

Đây là kết quả đáng giá nhất của M2.

Bốn câu bị `Semantic drift` có `rank_delta = 0`: q-016, q-022, q-034, q-039. Riêng
**q-039** là ví dụ sạch nhất:

```text
question_vi   : Khóa học phân biệt kiểm thử hộp đen và kiểm thử hộp trắng như thế nào?
frozen literal: How do black box testing and white box testing differ?
machine output: Black box testing
rank_delta    : 0
top_3_overlap : 3/3   ← Top-3 trùng hoàn toàn với bản dịch người
adjudication  : Semantic drift
```

Bản dịch mất hẳn vế white-box và mất luôn intent so sánh, nhưng **mọi chỉ số retrieval
đều không phản ứng**. Nếu M2 chỉ đặt G2, kết luận sẽ là "tụt nhẹ, chấp nhận được".

Kết luận rút ra: với bài toán dịch-rồi-truy-xuất, retrieval metric là điều kiện cần
chứ không đủ. Gate dạng hội giữa một **metric tự động** và một **phán đoán ngữ nghĩa
của người** là thiết kế đúng, và M2 cung cấp bằng chứng thực nghiệm cho điều đó thay
vì chỉ lập luận.

## Determinism

Run A và run B khác nhau ở `q-001`, tại `temperature = 0`, `seed = 42`.

Phạm vi kết luận: đây là phép đo **riêng cho literal translator**. Nó cho thấy các
deterministic-rerun guarantee trước đây của repository **không thể mặc định suy rộng
sang Ollama generation nói chung**. Nó **không** phải bằng chứng về G0 English
generator; muốn kết luận riêng cho G0 thì phải có test G0 riêng.

## P1 — đọc trung thực

`P1 = PASS`, nhưng là pass kỹ thuật. Criterion A không thỏa: câu tụt rank nặng nhất là
q-014 (delta `108`), không phải q-008 (delta `20`). P1 chỉ đậu nhờ criterion B, nơi
q-008 hòa với q-033 và q-037 tại `top_3_overlap = 0`. Rule đã đăng ký cho phép hòa nên
PASS hợp lệ và không được sửa hậu nghiệm. Nhưng dự đoán thực chất — "q-008 sẽ là câu
nhạy nhất" — **không được dữ liệu ủng hộ**.

## Quy trình

1. Verify SHA-256 của toàn bộ input đã đăng ký và runtime source; dừng nếu có gì thay đổi.
2. Chạy translator runtime **hai lần** trên 20 `question_vi` → determinism check ở
   temperature 0 / seed 42. Ghi token counts, latency và cờ chạm trần `num_predict=128`.
3. Dense full ranking 861 trên `machine_literal_en`, cùng canonical Ground Truth.
4. So ba nhánh: `question_en`, frozen `literal_en`, `machine_literal_en`.
5. Đánh giá G2 và P1 tự động; G1 do người duyệt.

Metric dùng lại **đúng hàm `branch_metrics` của M3 Phase 9** bằng import, không
reimplement, nên định nghĩa relevance và recall không thể lệch khỏi baseline.

## Chạy

```powershell
python -X utf8 scripts/evaluation/run_multilingual_runtime_translation_v1_m2.py
python -X utf8 scripts/evaluation/freeze_multilingual_runtime_v1_m2.py
```

Runner cần Ollama chạy với `llama3.2:3b` đúng digest đã pin. Đây là batch measurement
gọi trực tiếp translator; **không** dựng API server và **không** gọi generator. Runner
từ chối ghi đè nếu artifact kết quả đã tồn tại. Script freeze chỉ ghi nhận kết quả đã
có, không chạy lại model.

## Điều bị cấm sau khi thấy kết quả

Sửa prompt dịch, tham số translator hoặc retriever; sửa artifact Phase 9 hoặc Ground
Truth; chạy lại với tham số khác rồi báo cáo lần tốt hơn; sửa bản dịch hậu nghiệm;
định nghĩa lại gate hoặc dự đoán. FAIL không cho phép sửa nhanh — nó có nghĩa nhánh
VI chưa được chấp nhận là fidelity-preserving, và mọi phản ứng là một quyết định
thuộc milestone riêng.

## Lưu ý cho milestone sau

20 paired intents này **đã bị dùng làm dev set**: kết quả từng câu đã được quan sát và
adjudicate. Mọi phương án khắc phục nếu được đánh giá lại trên đúng bộ 20 câu này sẽ là
so sánh contaminated. Cần một bộ paired thứ hai hoặc một holdout được tách trước.
