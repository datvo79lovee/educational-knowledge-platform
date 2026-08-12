# Chunking experiment reports

Folder này chứa validation metadata cho Gold chunk sample của MIT 6.0001. Report
không chứa `chunk_text`, Silver transcript text hoặc embedding vector.

```text
sample_chunk_validation.csv
sample_chunk_cross_process_validation.csv
full_chunk_validation.csv
full_chunk_cross_process_validation.csv
chunking_retrieval_results.csv
chunking_comparison.csv
retrieval_run_manifest.json
retrieval_cross_process_validation.csv
canonical_gold_manifest.json
canonical_gold_validation.csv
canonical_gold_cross_process_validation.csv
```

`sample_chunk_validation.csv` ghi metrics và validation của ba configuration trên năm
video sample. `sample_chunk_cross_process_validation.csv` xác minh hai Python process
độc lập tạo cùng SHA-256 cho từng configuration.

`full_chunk_validation.csv` ghi cùng bộ validation trên đủ 38 video Silver.
`full_chunk_cross_process_validation.csv` xác minh hai Python process độc lập tạo
cùng SHA-256 cho từng full-corpus configuration.

Tạo lại sample và validation trong process:

```powershell
python -X utf8 scripts/chunking/build_chunk_samples.py
```

Xác minh cross-process:

```powershell
python -X utf8 scripts/chunking/verify_chunk_samples_cross_process.py
```

Gold JSONL tương ứng nằm trong `data/gold/mit_60001/samples/` và bị gitignore.

Build ba full-corpus candidate configuration:

```powershell
python -X utf8 scripts/chunking/build_chunk_samples.py --mode full
```

Xác minh full build qua hai process:

```powershell
python -X utf8 scripts/chunking/verify_chunk_samples_cross_process.py --mode full
```

Full candidate JSONL nằm trong `data/gold/mit_60001/experiments/<config_id>/` và
bị gitignore. Đây chưa phải canonical `data/gold/mit_60001/chunks.jsonl`; chỉ sau
retrieval comparison và human decision mới chọn một configuration để tạo Gold full.

## Dense retrieval comparison

Chạy dense retrieval cho 35 câu `approved` có answer; năm câu
`out_of_scope` không tham gia tính retrieval metrics:

```powershell
python -X utf8 scripts/chunking/evaluate_chunk_retrieval.py
```

Relevance được xác định khi chunk và Ground Truth cùng video và giao nhau
theo chỉ số Silver segment. Report chi tiết lưu top 10 metadata cho mỗi câu,
không lưu `chunk_text`; `manual_judgment` để trống cho human citation review.

Xác minh ba retrieval artifact ổn định qua hai Python process độc lập:

```powershell
python -X utf8 scripts/chunking/verify_retrieval_cross_process.py
```

`chunking_retrieval_results.csv` chứa kết quả theo câu hỏi;
`chunking_comparison.csv` chứa metrics tổng hợp theo configuration;
`retrieval_run_manifest.json` khóa model revision, input hash và quy tắc xếp hạng;
`retrieval_cross_process_validation.csv` ghi hash của hai lần chạy.

Raw dense retrieval output không tự chọn configuration thắng. Human review cuối
cùng nằm tại
`evaluation/review/chunking/mit_60001_chunking_citation_review_2026-08-11_reaudited.xlsx`
và quyết định có thể audit nằm tại
`evaluation/review/chunking/mit_60001_chunking_configuration_decision_2026-08-12.csv`.

Configuration được human approve ngày 2026-08-12 là:

```text
semantic_cosine_wp240_v1
```

`manual_citation_review_status=pending` trong `chunking_comparison.csv` được giữ
nguyên vì file này là raw deterministic output đã qua cross-process hash validation;
không sửa tay field đó. Decision CSV là nguồn trạng thái human review sau retrieval.

Promote configuration đã chọn thành canonical Gold full:

```powershell
python -X utf8 scripts/chunking/promote_selected_config.py
```

Xác minh promotion qua hai Python process:

```powershell
python -X utf8 scripts/chunking/verify_canonical_gold_cross_process.py
```

Canonical `data/gold/mit_60001/chunks.jsonl` đã được build từ
`semantic_cosine_wp240_v1`: 861 chunks, 38 video, phủ đủ 12.518 Silver segments,
SHA-256 `c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432`.
Output byte-identical với selected candidate; schema, lineage, source text/timing/hash,
chunk ID/index và coverage validation đều pass. Canonical JSONL là generated data và
bị gitignore; manifest cùng validation reports được giữ trong folder này.
