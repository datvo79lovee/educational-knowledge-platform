# Dense Retrieval/Search API validation

Folder này chứa bằng chứng implementation và validation của Phase 7 Search API trên
canonical MIT 6.0001 Fall 2016 corpus.

## Runtime đã khóa

```text
Flow              : Question -> Dense Top 3 evidence
Retrieval method  : dense_baseline_v1
Index run ID      : mit60001_index_558e4d6e873847dd
Corpus            : 861 chunks / 38 videos
Endpoints         : POST /search, GET /videos/{video_id}
Score tolerance   : 1e-6
Repeat count      : 2
```

Search result gồm chunk text, score, video metadata, start/end timestamp, source URL
và timestamped citation URL.

## Validation result

| Kiểm tra | Kết quả |
| --- | ---: |
| Answerable Top 3 IDs khớp baseline | 35/35 |
| Answerable Top 3 scores trong tolerance | 35/35 |
| Maximum observed score delta | 0,0000004138 |
| Out-of-scope giữ retrieval-only behavior | 5/5 |
| Repeated response match | 40/40 |
| Video metadata | 38/38 |
| Citation URL/timestamp/text | 120/120 |
| HTTP failure cases | 9/9 |
| Startup failure cases | 7/7 |
| Unit tests | 5/5 |
| Cross-process byte-identical artifacts | 6/6 |

Score delta đến từ khác biệt float32 giữa baseline batch encoding và API
single-query encoding. Nó nhỏ hơn tolerance `1e-6` và không thay đổi Top 3 IDs hoặc
ranking.

## Hai loại validation không được trộn lẫn

`Recall@3 = 0.742857143` là retrieval metric trên Ground Truth benchmark. Top 3 IDs
khớp baseline 35/35 chỉ chứng minh Search API tái tạo đúng retriever đã khóa. Nó không
có nghĩa cả 35 câu đều có evidence đúng trong Top 3.

## Ranh giới hiện tại

Đã hoàn thành:

- Dense retrieval runtime;
- Top 3 evidence;
- citation URL và timestamp;
- video metadata;
- deterministic validation.

Chưa làm:

- answer question;
- evidence accept/reject;
- abstain cho out-of-scope;
- LLM grounded generation;
- answer groundedness hoặc abstention accuracy end-to-end.

Năm out-of-scope questions cố ý trả HTTP `200` và Dense Top 3. Validator xác nhận
response không có `answer`, `accepted`, `rejected`, `abstain` hoặc `decision`.

## Lệnh chạy

```powershell
python -X utf8 -m pytest tests/search_api/search_api_validation_test.py -q
python -X utf8 scripts/api/validate_search_api.py
python -X utf8 scripts/api/verify_search_api_cross_process.py
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

## Artifact

```text
search_api_answerable_validation.csv
search_api_out_of_scope_validation.csv
search_api_video_validation.csv
search_api_failure_validation.csv
search_api_citation_validation.csv
search_api_validation_manifest.json
search_api_cross_process_validation.csv
```
