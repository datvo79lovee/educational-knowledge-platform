# Multilingual Runtime V1 — M2: machine translation fidelity

## Trạng thái

`preregistered_not_executed`. Gate và dự đoán đã được khóa tại
[`m2_preregistration.json`](m2_preregistration.json) **trước khi** chạy bất kỳ
translator call nào. Chưa có kết quả nào trong thư mục này.

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

| ID | Điều kiện | Ngưỡng |
|---|---|---|
| G1 | `Semantic drift` theo rubric M1 | đúng `0` |
| G2 | Recall@3 của `machine_literal_en` so với frozen `literal_en` (0,70) | `>= 0,65` |

Dự đoán đăng ký trước **P1**: `mit60001-q-008` tiếp tục là intent nhạy nhất với
translation, thao tác hóa thành: nó xếp tệ nhất ở ít nhất một trong hai chỉ số —
mức tụt first-relevant-rank lớn nhất, hoặc Top-3 overlap thấp nhất.

G1 **không thể** đóng bằng máy. Script sinh
`m2_adjudication_worksheet.csv`; người duyệt gán nhãn theo đúng rubric M1
(`Equivalent` / `Minor wording difference` / `Semantic drift`). Các dòng trùng chuỗi
tuyệt đối với frozen `literal_en` được tự động gán `Equivalent`.

## Quy trình

1. Verify SHA-256 của toàn bộ input đã đăng ký; dừng nếu có gì thay đổi.
2. Chạy translator runtime **hai lần** trên 20 `question_vi` → determinism check ở
   temperature 0 / seed 42. Ghi token counts, latency và cờ chạm trần
   `num_predict=128`.
3. Dense full ranking 861 trên `machine_literal_en`, cùng canonical Ground Truth.
4. So ba nhánh: `question_en`, frozen `literal_en`, `machine_literal_en`.
5. Đánh giá G2 tự động; G1 chờ người duyệt.

Metric dùng lại **đúng hàm `branch_metrics` của M3 Phase 9** bằng import, không
reimplement, nên định nghĩa relevance và recall không thể lệch khỏi baseline.

## Chạy

```powershell
python -X utf8 scripts/evaluation/run_multilingual_runtime_translation_v1_m2.py
```

Cần Ollama chạy với `llama3.2:3b` đúng digest đã pin. Đây là batch measurement gọi
trực tiếp translator; **không** dựng API server và **không** gọi generator. Live HTTP
integration và latency budget thuộc M3.

## Điều bị cấm sau khi thấy kết quả

Sửa prompt dịch, tham số translator hoặc retriever; sửa artifact Phase 9 hoặc Ground
Truth; chạy lại với tham số khác rồi báo cáo lần tốt hơn; sửa bản dịch hậu nghiệm;
định nghĩa lại gate hoặc dự đoán. FAIL không cho phép sửa nhanh — nó có nghĩa nhánh
VI chưa được chấp nhận là fidelity-preserving, và mọi phản ứng là một quyết định
thuộc milestone riêng.
