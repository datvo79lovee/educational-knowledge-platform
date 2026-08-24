# Multilingual Runtime V1 — M5: can thiệp contract-abstention tiếng Việt

Status: `m5_1_preparation_complete_not_executed`.

Pre-registration revision 5 SHA-256:
`4373ab68698011b1e182fb84aef2cfd0404969ad66c4850717ae7b4a2ba585e3`.

Can thiệp prompt **đã được áp dụng** vào runtime; execution **chưa** chạy và chưa có
model output M5 nào. Mọi revision đều viết trước execution.

## Mục tiêu

M4 đã freeze một phép đo runtime: 8/20 record lỗi, toàn bộ ở
`generation_contract`, và mọi raw payload lỗi chọn `decision="abstain"`.
M5 kiểm chứng **một** can thiệp prompt hẹp có giảm các vi phạm shape của abstention
hay không. M5 không đánh giá answer quality, groundedness, citation support hay
parity với English.

## Can thiệp duy nhất được phép trong M5.1

Chỉ sửa `VI_SYSTEM_PROMPT` trong `src/grounded_answer/prompts.py` để thay chỉ dẫn
ngôn ngữ vô điều kiện bằng chỉ dẫn có điều kiện theo decision:

```text
decision="answer"  -> viết answer bằng tiếng Việt
decision="abstain" -> answer=null và supporting_chunk_ids=[]
```

`SYSTEM_PROMPT`, user prompt, strict Pydantic contract, normalization, translator,
generator model/digest/config, Dense/index/metadata, Ground Truth, 20 intent và
application citation mapping đều không được đổi.

Đây là một giả thuyết kiểm chứng được, không phải kết luận từ M4 rằng prompt là
nguyên nhân. Nếu gate fail, rollback là hoàn nguyên đúng thay đổi prompt này; không
mở thêm prompt tweak, normalization, retry, model hoặc retrieval experiment trong
cùng milestone.

## M5.1 execution đã đăng ký trước

- Input: đúng 20 intent và artifacts M4 đã freeze, tham chiếu SHA trong
  `m5_preregistration.json`.
- Một attempt, chạy 20 intent, continue-after-failure, zero retry và atomic flush sau
  từng intent.
- Thu raw generator payload, translation query, Top 3 và stage telemetry trên success
  lẫn error path.
- Rehash runtime source trước và sau execution; runner/analysis code phải được pin
  trước khi gọi model.
- Không human review và không tính metric chất lượng ở M5.1.

## Gate M5.1

| Gate | Điều kiện | Runner thực thi ở đâu |
| --- | --- | --- |
| G1 execution integrity | 20/20 record **đúng ID và đúng thứ tự** đã đăng ký; mỗi record passed có **1 translation + 1 retrieval + 1 generation**; stage totals đạt 20 khi run sạch; mọi record thỏa **yêu cầu diagnostic theo stage**; zero retry; runtime hash khớp **trước và sau** execution | `evaluate_gates`, `diagnostic_gaps` |
| G2 runtime failure | `total_runtime_failure_count = 0` trên **mọi** failure layer | `evaluate_gates` |
| G3 scope integrity | Chỉ file prompt được phép khác so với baseline M4, **và từng symbol được pin bên trong file đó đều khớp** | `scope_integrity_report`, `prompt_symbol_report` |

M5.1 PASS khi G1–G3 đều PASS.

### Lỗ hổng gate đã được đóng ở revision 2

Revision 1 định nghĩa G2 là `generation_contract failure count = 0`. Một lần chạy có
thể thỏa điều đó **trong khi vẫn hỏng** ở tầng translation hoặc provider — tức đổi một
loại lỗi lấy một loại lỗi khác rồi vẫn PASS. G2 nay đếm **toàn bộ** runtime failure;
`generation_contract_failure_count` vẫn được báo riêng làm chẩn đoán.

Gate là zero-tolerance chứ không phải một tỉ lệ kèm khoảng tin cậy: một payload không
thỏa strict contract là **runtime failure**, không phải metric chất lượng, nên không có
lập luận cỡ mẫu nào để dung thứ một lỗi ở n=20.

### Không được nới contract để pass

Pre-registration ghi rõ: cấm làm strict contract dễ hơn, cấm mở rộng normalization để
hấp thụ một abstention hỏng, cấm thêm retry, cấm chọn lần chạy đẹp hơn.
`contracts.py`, `service.py` và hai rule normalization hiện có đều nằm trong danh sách
đóng băng và được pin hash.

## Scope integrity kiểm được bằng máy

Runner chứng minh phạm vi bằng **hai lớp độc lập**:

**Lớp 1 — file.** So từng runtime source hash với pin của M4. Quan sát tại
pre-registration: đúng một file `src/grounded_answer/prompts.py`.

**Lớp 2 — từng symbol bên trong file đó.** Cấp file là chưa đủ: `prompts.py` còn chứa
EN prompt, nhãn version EN và `build_user_prompt`. Nếu chỉ kiểm cấp file, một sửa đổi
bất kỳ trong file vẫn ẩn được dưới danh nghĩa "authorized file".

| Symbol | Vai trò |
|---|---|
| `en_system_prompt_sha256` | frozen |
| `en_prompt_version` | frozen |
| `build_user_prompt_source_sha256` | frozen |
| `vi_system_prompt_sha256` | authorized candidate |
| `vi_prompt_version` | authorized candidate |

`scope_integrity.prompt_symbols` là **single source of truth** cho pin prompt. Có test
parametrize khẳng định drift ở **bất kỳ** symbol nào trong năm cũng làm G3 FAIL.

Cả hai lớp chạy **trước** execution (raise + không tạo artifact nếu FAIL) và chạy lại
**sau** execution, ghi vào manifest.

## Yêu cầu diagnostic theo stage

Pipeline là tuần tự: retrieval chỉ chạy sau khi translation trả về, generation chỉ chạy
sau khi retrieval trả về. Nên yêu cầu phải **có điều kiện theo stage đã chạy thật**:

| Điều kiện | Trường bắt buộc |
|---|---|
| mọi record failed | `failure_layer`, `error_type` |
| translation đã chạy | `translation_latency_ms` |
| retrieval đã chạy | `retrieval_query`, `retrieval_latency_ms` |
| generation đã chạy | `retrieval_query`, `top3_chunk_ids`, `raw_model_output`, `generation_latency_ms`, `generation_prompt_eval_count`, `generation_eval_count` |

Đòi Top-3 từ một lỗi tầng translation là sai; **không** đòi nó từ một lỗi tầng
generation chính là mất dữ liệu mà M3 attempt 1 đã gặp. Có negative test cho **từng**
trường bị thiếu, và một test khẳng định lỗi tầng translation không bị đòi diagnostic
của stage chưa chạy.

## Can thiệp thực tế

```python
VI_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\nIf you answer, write the answer field in Vietnamese."
    "\nIf you abstain, set answer to null and supporting_chunk_ids to an empty list."
)
```

Hai dòng này đối ứng trực tiếp với hai biến thể vi phạm mà M4 đo được: 6 lần
`abstain` + answer khác null, và 2 lần `abstain` + `supporting_chunk_ids` không rỗng.

Hợp đồng phạm vi được phát biểu lại cho đúng: **một prompt artifact change gồm đúng
hai symbol** — `VI_SYSTEM_PROMPT` là thay đổi **behavioral** duy nhất, và
`VI_PROMPT_VERSION` chỉ mang **identity/provenance**, không phải thay đổi hành vi.
`behavioral_change_count = 1`, `symbol_count = 2`.

Lý do nâng version: repository đã coi một nhãn version trỏ tới hai nội dung khác nhau
là defect — chính lý do prompt English từng phải khôi phục về byte-identical v1.

## Bước sau

M5.1 preparation và pre-registration runner đã hoàn tất. Bước kế tiếp là commit riêng
phần preparation để chứng minh contract có trước kết quả, rồi xin phê duyệt execution.
Chỉ nếu M5.1 PASS mới mở M6: human evaluation E2E Vietnamese.
