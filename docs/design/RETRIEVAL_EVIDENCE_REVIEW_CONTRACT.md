# Retrieval evidence review contract v2 — archived experiment contract

> Trạng thái từ 2026-08-20: contract này được giữ để audit Phase 8 nhưng không còn
> là contract của active runtime. Evidence Reviewer đã bị loại khỏi final runtime
> architecture sau khi Baseline V1, Prompt V2 và A1 không đạt frozen quality gate.
> Không tiếp tục V2.1, A1.1 hoặc A2 trong scope project hiện tại.

Active target architecture:

```text
Question
  -> validated Search API
  -> Dense Top 3 evidence
  -> Grounded Answer Generator
       -> Answer + supporting chunk IDs + video URL + timestamp
       -> hoặc Abstain khi evidence không đủ
```

## Mục tiêu lịch sử

Contract này khóa gate kiểm tra evidence sau Dense Search API của corpus MIT 6.0001
Fall 2016. Gate này chỉ quyết định ba candidate chunks có đủ bằng chứng trực tiếp
để trả lời câu hỏi hay không; nó không thay thế Ground Truth và không sửa Silver,
Gold hoặc evaluation canonical.

Flow dưới đây là flow experiment đã được đánh giá, không còn là active runtime:

```text
Question
  -> validated Search API
  -> Dense Top 3 evidence
  -> Evidence review: accept | reject
  -> [accept only, milestone sau] candidate Answer Points
```

Flow `Hybrid Search -> Cross-Encoder -> Top 3` trong contract v1 đã lỗi thời.
Retrieval production đã khóa là `dense_baseline_v1`; Cross-Encoder chỉ còn là
experiment không được chọn.

## Phạm vi M2A và ranh giới

- M2A là provider-independent: khóa contract, request/response schema, retrieval
  identity, package 40 câu và calibration reference.
- M2A không cài SDK, không gọi provider, không tạo output review và không tạo
  Answer Points.
- Mỗi request chỉ chứa question và đúng Dense Top 3 trả về qua `POST /search`.
- Reviewer không được dùng kiến thức ngoài ba candidate chunks.
- `accept` và `reject` là quyết định về **candidate evidence**, không phải quyết
  định question đúng/sai và không tự động sửa Ground Truth.
- Out-of-scope vẫn được Search API trả Top 3. Abstain/reject chỉ thuộc evidence
  review layer, không thuộc retrieval API.

## Retrieval identity đã khóa

Mọi request và response phải mang cùng identity:

```text
retrieval_method              = dense_baseline_v1
index_run_id                  = mit60001_index_558e4d6e873847dd
search_api_validation_run_id  = mit60001_search_api_35767a6f304c4dc3
top_k                         = 3
```

Nếu một trong bốn giá trị đổi, package phải được build lại và nhận hash/run ID
mới. Không được ghép response của retrieval run khác vào package hiện tại.

## Request schema

Mỗi dòng của package input phải pass
`schemas/evidence_review_request_v1.schema.json` và có:

```text
schema_version
request_id
question_id
question
scope_version
retrieval_identity
candidates[3]
```

`candidates` giữ nguyên rank, chunk ID, text, score, video metadata, time range và
citation URL từ Search API. Rank phải đúng `1, 2, 3`; chunk ID phải duy nhất.
Package không chứa expected answer points hoặc credited Ground Truth ranges để
tránh làm rò nhãn vào reviewer runtime.

## Quy tắc quyết định và response schema

Output tương lai phải pass `schemas/evidence_review_response_v1.schema.json`.

- `accept`: Top 3 có đủ evidence trực tiếp để trả lời question mà không cần suy
  đoán ngoài transcript; `supporting_chunk_ids` có ít nhất một ID và chỉ được là
  tập con của ba `top3_chunk_ids`.
- `reject`: evidence thiếu, chỉ liên quan chung chung, mâu thuẫn hoặc question
  ngoài target scope; `supporting_chunk_ids` bắt buộc là `[]`.
- Không có confidence bucket hoặc nhãn thứ ba trong runtime output.
- `decision_reason` là lý do audit ngắn, không phải Ground Truth mới.

Response schema khóa cả execution identity: provider, model identifier, API mode,
temperature hoặc reasoning setting, structured-output schema version,
prompt/contract version và retrieval identity. API key tuyệt đối không được ghi
vào request, response, manifest hoặc report.

## Calibration reference

Calibration reference được suy ra từ evaluation Ground Truth và locked Dense
baseline để đánh giá reviewer; nó không được đưa vào prompt/runtime request.

```text
strong_accept       = 16 câu có full credited Ground Truth coverage trong Top 3
strong_reject       = 12 câu: 5 out-of-scope + 7 retrieval miss không có audit flag
needs_human_review  = 12 câu: 10 partial coverage + q-023/q-041 có audit flag
```

`needs_human_review` không phải nhãn runtime và không được chuyển thành
`accept/reject` giả. Hai câu q-023 và q-041 được giữ riêng vì human reranking note
nêu khả năng Ground Truth under-credit evidence hợp lệ.

## Retrieval ceiling và phân loại lỗi ở M3

Với 35 câu answerable, Dense Top 3 hiện có full coverage 16 câu, partial coverage
10 câu và không có credited evidence 9 câu. Reviewer chỉ được nhìn Top 3 nên không
thể cứu một retrieval miss nếu evidence đúng không vào candidate pool.

M3 phải báo tách riêng:

- `retrieval_miss`: credited evidence không có trong Top 3; reviewer không có cơ
  hội chọn đúng.
- `reviewer_error`: evidence cần thiết có trong Top 3 nhưng reviewer quyết định
  hoặc chọn supporting chunk sai.

Không được gộp hai loại lỗi này thành một accuracy duy nhất rồi kết luận về chất
lượng reviewer.

## Kết quả triển khai và trạng thái đóng

M2B sau đó đã được triển khai bằng Ollama `llama3.2:3b`; baseline V1 chạy đúng
structured-output contract nhưng có FAR `56,25%`. Prompt V2 giữ FAR `56,25%` và
evidence precision 37-scope giảm còn `68,66%`. A1 two-stage đạt runtime/stability
contract nhưng reject toàn bộ 37 câu evaluable: accept recall `0%`, FAR `0%`, final
selected pairs `0`, evidence precision `N/A`.

A1 được freeze là `failed_candidate`; Evidence Reviewer research dừng theo stopping
rule. Code experiment, schemas, human review, metrics, manifests và reports được giữ
lại. API/runtime production path không được gọi Evidence Reviewer và không dùng
reviewer quality gate để chặn Grounded Answer Generator.
