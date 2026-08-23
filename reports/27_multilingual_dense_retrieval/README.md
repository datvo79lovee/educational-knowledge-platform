# Phase 9 M2 — Multilingual Dense retrieval run

## Scope

M2 đọc nguyên `question_en` và `literal_en` từ M1 paired artifact đã freeze rồi
chạy cả hai qua cùng `dense_baseline_v1`. Không chạy translator, BM25, RRF,
reranker, generator hoặc bất kỳ retrieval experiment mới nào.

```text
question_en → dense_baseline_v1
literal_en  → dense_baseline_v1
```

## Retrieval depth

Canonical Dense evaluation xếp hạng toàn bộ 861 chunks để xác định first relevant
rank; Top 10 trước đây chỉ là phần export. Vì M2 chưa dùng Ground Truth và M3 phải
giữ đúng MRR semantics, M2 export full ranking 861 cho mỗi query. M3 có thể lấy
Top 1/3/5 trực tiếp từ cùng output mà không chạy retrieval lại.

## Artifacts

- `multilingual_dense_retrieval_results.jsonl`: 40 records, mỗi record chứa full
  ranking 861 chunks.
- `multilingual_dense_retrieval_manifest.json`: khóa M1, Gold/index, encoder,
  retrieval config, counts và artifact hash.
- `multilingual_dense_retrieval_cross_process_validation.json`: kiểm tra hai fresh
  Python processes tạo output byte-identical.

## Boundary

M2 không tính MRR, Recall, Full Evidence hoặc delta chất lượng. Không có human
review retrieval output. Các phép tính relevance và Top-3 overlap thuộc M3.

## Final validation

- EN branch: 20/20 queries.
- Frozen `literal_en` branch: 20/20 queries.
- Retrieval records: 40/40, mỗi record có 861 ranks.
- Missing intents / duplicate branches / invalid chunk IDs: 0 / 0 / 0.
- EN Top 10 IDs và scores khớp canonical Dense baseline: 20/20.
- Hai exact-string pairs (`mit60001-q-003`, `mit60001-q-022`) có full retrieval
  results giống hệt giữa hai branches: 2/2.
- Translator, LLM và generator calls: 0.
- Cross-process results/manifest byte-identical: `passed`.
- Quality metrics computed: `false`.

Artifact hashes:

```text
results  244861f3535e2875dee2c3dcd31b0b2af3ecdad91edf43e7af26abef02af3991
manifest e6cf25326dd92961e79d932aab615ff38a1b428a06c39acac83eb6de98221e93
cross-process e75017d930a66f4adafe30f8957fbbe0dfb001c5e6921dbe816eb61018de193b
```

```powershell
python -X utf8 scripts/evaluation/run_multilingual_dense_retrieval_m2.py
python -X utf8 scripts/evaluation/verify_multilingual_dense_retrieval_m2_determinism.py
python -X utf8 scripts/evaluation/validate_multilingual_dense_retrieval_m2.py
```
