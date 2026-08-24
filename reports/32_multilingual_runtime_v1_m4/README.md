# Multilingual Runtime V1 — M4: đo tỉ lệ lỗi runtime tiếng Việt

Status: `frozen_runtime_failure_measurement`.

M4 attempt 1 đã chạy đủ 20 intent và được freeze tại
`m4_final_manifest.json`. Đây là measurement runtime failure, không phải đánh giá
quality câu trả lời tiếng Việt.

Pre-registration revision 3 SHA-256:
`229f4597448f723aeacbb83899192fdaf5341154e7561eebb1774d7fdf176921`.

Mọi revision đều được khóa **trước execution** và trước khi có hoặc quan sát bất kỳ
kết quả M4 nào.

**Revision 2** sửa ba lời hứa mà runner chưa thực thi: I4 không được kiểm lại sau
execution, raw output chỉ ghi sau cả loop nên một lần gián đoạn có thể mất sạch record,
và per-stage latency cùng token count đã đăng ký lại thiếu trên error path. R2 khóa
atomic flush sau từng intent, rehash runtime sau execution kèm ghi kết quả thật, và
recorder thứ ba bọc generation provider.

**Revision 3** đóng nốt analysis layer. R1 và R2 đã pin hash của runner này và của
runner M3 được import, nhưng **không ai kiểm chúng** — đúng cùng lớp lỗi với I4, chỉ
khác là áp lên code đo thay vì code chạy. R3 bắt runner verify cả hai analysis script
**trước mọi model call** và re-pin hash của chính nó.

Runtime, prompt, model, retriever, normalization, frozen input, execution order, phân
tầng lỗi, integrity conditions và quyết định không có promotion gate đều **không đổi**
qua cả ba revision.

## Analysis code được pin VÀ được kiểm

```text
scripts/evaluation/run_multilingual_runtime_v1_m4.py    3ae14843...
scripts/evaluation/run_multilingual_runtime_v1_m3.py    cf3e50c0...   (import wilson_interval)
```

Runner băm lại cả hai trước khi load encoder và trước mọi Ollama call; lệch thì raise
và không tạo artifact nào.

Ranh giới của cơ chế này được ghi thẳng vào pre-registration: nó phát hiện **drift** —
code đổi sau khi đăng ký mà không đăng ký lại — chứ **không** chống được một lần sửa
đồng thời viết lại pre-registration. Nó không được claim là chống đối thủ có chủ đích.

Bằng chứng cơ chế hoạt động: sau khi thêm check vào runner mà chưa re-pin, runner **tự
chặn chính nó**:

```text
ValueError: Analysis code changed since pre-registration:
scripts/evaluation/run_multilingual_runtime_v1_m4.py
```

Đây là negative control thật, quan sát được, không phải mô phỏng.

## Vì sao có milestone này

M3 attempt 1 dùng stop-on-first-failure. Nó dừng ở intent thứ hai, cho 2/20 record và
không ước lượng được gì. Stop-on-first-failure là gate toàn vẹn đúng cho hệ thống
**được tin là toàn vẹn**; nó triệt tiêu năng lực đo với hệ thống có tỉ lệ lỗi **chưa
biết**.

M4 đổi **dụng cụ đo**, không đổi runtime.

## Câu hỏi nghiên cứu

> Trên 20 paired intents đã freeze, runtime tiếng Việt lỗi bao nhiêu lần, và mỗi lỗi
> nằm ở tầng nào?

M4 **không** phát biểu gì về chất lượng câu trả lời tiếng Việt.

## Runtime không đổi so với M3

`runtime_unchanged_since_m3.verified = true`. Sáu file runtime mà M3 pin được băm lại
tại thời điểm pre-registration M4 và khớp **từng giá trị**:

```text
src/search_api/service.py
src/grounded_answer/service.py
src/grounded_answer/prompts.py
src/grounded_answer/contracts.py
src/grounded_answer/ollama_provider.py
src/multilingual/translation.py
```

Nghĩa là M4 đo đúng runtime mà M3 đã thử, nên hai milestone so được với nhau. Một test
khóa bất biến này bằng cách so trực tiếp hai pre-registration.

## Đổi dụng cụ đo

| Thuộc tính | M3 | M4 |
|---|---|---|
| Gặp runtime failure | dừng ngay | ghi record rồi **chạy tiếp** |
| Số intent thu được | 2/20 | dự kiến 20/20 |
| Retry | 0 | 0 |
| Chọn output đẹp | không | không |
| Promotion gate | G1–G4 | **không có** |

## Quan sát mà không sửa runtime

Đây là ràng buộc khó nhất của M4: cần đủ chẩn đoán trên error path nhưng **không được
sửa một dòng runtime nào**. Hai cơ chế, cả hai đã kiểm chứng:

**Wrapper thuần delegation.** Runner tự dựng `GroundedAnswerService`, nên nó bọc
translator và Dense search service bằng recorder chỉ ghi lại kết quả rồi trả nguyên
vẹn. Provider, prompt, model, digest, tham số decoding và index không đổi. Bề mặt phụ
thuộc rất nhỏ — service chỉ dùng `translate()`, `search()` và `index_run_id` — và test
khẳng định wrapper trả về **đúng cùng object** của inner.

Có **ba** recorder: translator (ghi `literal_en`, token, latency), search service (ghi
Top 3, latency, proxy `index_run_id`) và generation provider (ghi raw content, token,
latency **trước khi** strict validation chạy). Recorder thứ ba là điểm mấu chốt: khi
contract từ chối payload ở bước sau, chẩn đoán đã được giữ lại rồi.

**Exception chain (fallback).** `str(ValidationError)` cắt ngắn payload, nhưng
`errors()[0]["input"]` giữ nguyên toàn bộ; `json.JSONDecodeError.doc` giữ nguyên văn
bản chưa parse. Dùng khi không có generation call nào được ghi.

Thứ tự ưu tiên capture: generation recorder → ValidationError input → JSONDecodeError
doc. Đây chính là dữ liệu mà M3 attempt 1 đã mất ở `q-002`, và một test dựng lại đúng
tình huống đó bằng stub để chứng minh record mới giữ đủ `retrieval_query`,
`top3_chunk_ids`, raw payload, token count và latency từng stage.

## Độ bền khi bị gián đoạn

Raw output được flush **atomic sau từng intent** bằng ghi file tạm rồi `os.replace`,
nên gián đoạn ở intent N vẫn giữ N−1 record đã hoàn tất. Một test mô phỏng gián đoạn
bằng `BaseException` ở intent thứ ba và khẳng định hai record đầu vẫn nằm trên đĩa.

Revision 1 hứa điều này trong `external_interruption_policy` nhưng ghi JSONL một lần
sau cả loop, nên lời hứa không được thực thi.

## Phân tầng lỗi

```text
translation_contract   translation_provider   translation_other
generation_contract    generation_provider    runtime_other
```

Tầng ghi lại **runtime gãy ở đâu**, không phải bản dịch hay evidence có tốt về nghĩa
hay không.

## Không có promotion gate

M4 không có prior nào cho tỉ lệ lỗi, nên mọi ngưỡng đều hoặc là bịa sau khi thấy kết
quả, hoặc là tuỳ tiện trước đó. M3 đã cho thấy ngưỡng ±1 câu ở cỡ mẫu này có power
kém. Vì vậy M4 **báo cáo một phép đo và không ra quyết định accept/reject**.

Thay vào đó có bốn `integrity_conditions` (I1–I4) để xác nhận phép đo hợp lệ: đủ 20
record, 0 retry và tối đa một call mỗi stage mỗi intent, mọi record failed có
`failure_layer` + `error_type` + raw payload khi đã có generation call, và runtime hash
**vẫn khớp sau execution**.

I4 được thực thi thật: runner băm lại toàn bộ runtime source **sau** khi loop kết thúc,
ghi danh sách mismatch và PASS/FAIL vào `m4_execution_manifest.json`, và đặt
`validation_status: failed_integrity_conditions` nếu bất kỳ điều kiện nào hỏng. Ở
revision 1 điều kiện này chỉ tồn tại trên giấy.

## Giới hạn độ phân giải

20 intents: một lỗi làm tỉ lệ dịch 0,05 và Wilson CI vẫn rộng. Quan trọng hơn,
**translator đã được chứng minh không deterministic ở temperature 0** (M2). Nên con số
M4 thu được là **một mẫu của quá trình lỗi**, không phải kỳ vọng của nó. Báo cáo phải
đi kèm khoảng tin cậy, không trích điểm ước lượng đứng một mình.

## Điều không được claim

Chất lượng câu trả lời tiếng Việt; so sánh parity với matched English baseline; diễn
giải lại M2 hoặc M3 đã freeze; production-ready; coi tỉ lệ quan sát được là tỉ lệ kỳ
vọng.

M3 gate G2–G4 vẫn `NOT_EVALUATED`. M4 không đánh giá chúng.

## Tái dùng output về sau

Raw output của M4 có thể được dùng lại bởi một milestone đánh giá chất lượng sau,
**chỉ khi** milestone đó đăng ký trước gate và rubric **trước khi** bắt đầu human
review. Review trước rồi đăng ký sau là không được phép.

## Kết quả attempt 1

```text
Executed / passed / failed       : 20 / 12 / 8
Runtime failure rate             : 8/20 = 0,400; Wilson 95% [0,219; 0,613]
Retry                            : 0
Integrity conditions I1–I4       : PASS
Runtime source rehash sau run    : 0 mismatch
```

Tất cả 8 failure thuộc `generation_contract`; không có translation failure,
generation provider failure hoặc runtime-other failure. Tất cả raw payload failure
chọn `decision="abstain"`; 12 record passed chọn `decision="answer"`. Sáu failure
là `abstain` kèm answer khác `null`; hai failure là `abstain` kèm answer `null` nhưng
`supporting_chunk_ids` không rỗng.

Raw generator payload, retrieval query, Top 3 và generation telemetry được capture
trên 8/8 failure. Đây là một execution sample: không được xem failure rate 0,400 là
tỉ lệ kỳ vọng, không được claim chất lượng VI/parity với English, và không được kết
luận prompt VI là nguyên nhân. Không có prompt, model, retriever hay normalization nào
được sửa bởi M4.

## Chạy

```powershell
python -X utf8 scripts/evaluation/run_multilingual_runtime_v1_m4.py --verify-only
python -X utf8 scripts/evaluation/run_multilingual_runtime_v1_m4.py
```

`--verify-only` kiểm 17 frozen inputs, 6 runtime source và thứ tự 20 intent, rồi
return **trước** khi load encoder và trước mọi Ollama call. Full execution cần Ollama
với `llama3.2:3b` đúng digest đã pin, và runner từ chối ghi đè nếu artifact kết quả đã
tồn tại.

Execution đầy đủ đã hoàn tất; runner sẽ từ chối ghi đè output artifact hiện có.
Không rerun attempt 1 để tìm output khác.
