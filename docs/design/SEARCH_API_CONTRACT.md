# Dense Retrieval/Search API Contract v1

## Phạm vi

Các retrieval endpoint trong contract này chỉ phục vụ canonical corpus MIT 6.0001
Fall 2016 và chỉ dùng `dense_baseline_v1`. `POST /search` trả ba evidence chunk; nó
không thực hiện LLM accept/reject, không sinh grounded answer và không tự xác định
câu hỏi out-of-scope. Application hiện có thêm `POST /answer`, nhưng endpoint đó là
Grounded Answer orchestration và không thay đổi contract retrieval-only của
`POST /search`.

## Source of truth

```text
Canonical Gold : data/gold/mit_60001/chunks.jsonl
Embeddings      : data/indexes/mit_60001/embeddings.npy
Metadata        : data/indexes/mit_60001/metadata.jsonl
Index manifest  : data/indexes/mit_60001/manifest.json
Decision        : docs/decisions/CANONICAL_RUNTIME_DECISIONS.md
```

API phải kiểm tra hash, shape, dtype, vector norm, chunk order, model revision và
canonical retrieval decision khi startup. Nếu validation thất bại, server không được nhận
request. Query encoder chỉ được load từ cache local bằng revision đã khóa.

## `POST /search`

Request:

```json
{
  "query": "What is the difference between a Python list and a dictionary?"
}
```

`query` được trim. Payload thiếu query, query rỗng, chỉ có whitespace hoặc có field
ngoài contract trả HTTP `422`.

Response hợp lệ luôn có đúng ba kết quả, sắp theo score giảm dần rồi `chunk_id` tăng
dần khi score bằng nhau:

```json
{
  "query": "What is the difference between a Python list and a dictionary?",
  "retrieval_method": "dense_baseline_v1",
  "index_run_id": "mit60001_index_558e4d6e873847dd",
  "result_count": 3,
  "results": [
    {
      "rank": 1,
      "chunk_id": "video-id:semantic_cosine_wp240_v1:0",
      "chunk_text": "...",
      "score": 0.5,
      "video_id": "video-id",
      "video_title": "Video title",
      "start_second": 120.5,
      "end_second": 160.2,
      "source_url": "https://www.youtube.com/watch?v=video-id",
      "citation_url": "https://www.youtube.com/watch?v=video-id&t=120s"
    }
  ]
}
```

`source_url` là canonical video URL. `citation_url` lấy phần nguyên dưới của
`start_second` để mở video tại đầu evidence chunk.

## `GET /videos/{video_id}`

Endpoint trả metadata tổng hợp từ canonical index:

```json
{
  "video_id": "video-id",
  "video_title": "Video title",
  "source_url": "https://www.youtube.com/watch?v=video-id",
  "chunk_count": 20,
  "start_second": 0.0,
  "end_second": 1200.0
}
```

Video ID không thuộc 38 target video trả HTTP `404`.

## Chạy local

Sau khi cài dependency trong `requirements.txt`, bootstrap đúng pinned query encoder
rồi chạy API:

```powershell
python -X utf8 scripts/bootstrap_query_encoder.py
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

Model và index được load một lần trong application lifespan. Startup không tự tải
model hoặc rebuild bất kỳ data artifact nào.

## Validation

Chạy unit test, full API validation và cross-process verification:

```powershell
python -X utf8 -m pytest tests/search_api/search_api_validation_test.py -q
python -X utf8 scripts/api/validate_search_api.py
```

Full validator gọi đủ 40 canonical questions qua ASGI HTTP hai lần mỗi câu. Với 35
answerable questions, Top 3 IDs phải khớp locked Dense baseline và score được so với
absolute tolerance `1e-6`. Sai lệch float32 lớn nhất của canonical run hiện tại là
`4.138e-7`; thứ hạng vẫn khớp 35/35.

Năm out-of-scope questions vẫn trả HTTP `200` và Dense Top 3. Đây là behavior đúng
của retrieval-only API, không phải abstention. Response không được chứa `answer`,
`accepted`, `rejected`, `abstain` hoặc `decision`.

`Recall@3 = 0.742857143` đo retrieval quality so với Ground Truth. Việc API Top 3
khớp baseline 35/35 chỉ đo implementation fidelity; hai chỉ số này không tương đương.

Validator không ghi file vào repo nếu không truyền tham số output. Khi cần giữ
manifest, caller phải chỉ rõ một file output, ví dụ
`--output tmp/search_api_validation.json`.

## Quan hệ với `POST /answer`

`POST /answer` gọi cùng `DenseSearchService`, lấy đúng Top 3 rồi thực hiện một local
Grounded Answer model call. Client không được truyền evidence tùy ý. Model chỉ trả
decision, answer, supporting chunk IDs và reason nội bộ; application kiểm tra IDs
thuộc Top 3 rồi map sang URL/timestamp thật. Không có LLM gate trung gian.

Grounded Answer Reliability V1 / G0 là canonical evaluated baseline: public runtime
success `40/40`, decision accuracy `23/37`, false abstain `11/21`
evidence-sufficient, false answer `3/16` evidence-insufficient và strict end-to-end
success `17/37`. Đây là descriptive in-sample result, không có pre-registered
quality gate và không phải production-ready claim. M3 cũ được giữ nguyên trong
historical report của nó; runtime hiện tại dùng Reliability V1.
