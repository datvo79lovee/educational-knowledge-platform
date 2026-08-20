# Phase 8 M2B — Local evidence reviewer runtime

M2B chạy evidence reviewer local trên đúng request package đã khóa ở M2A:

```text
canonical question + Dense Top 3
    -> Ollama / llama3.2:3b
    -> accept hoặc reject
    -> supporting_chunk_ids (chỉ được lấy từ Top 3)
```

## Ranh giới

- Runtime không đọc Ground Truth, calibration, `expected_answer_points` hoặc
  `relevant_time_ranges`.
- Model không được dùng tool, web search hoặc chunk ngoài Dense Top 3.
- `accept` phải có ít nhất một supporting chunk; `reject` phải có danh sách rỗng.
- M2B chưa sinh grounded answer và chưa đánh giá accuracy của reviewer.
- So sánh calibration, false accept/false reject và tách retrieval miss khỏi
  reviewer error thuộc M3.

## Runtime đã khóa

- Provider: `ollama`, local endpoint `http://127.0.0.1:11434`.
- Model: `llama3.2:3b`.
- Model digest:
  `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`.
- Quantization: `Q4_K_M`.
- `temperature=0`, `seed=42`, `num_predict=512`.
- Structured output: JSON Schema; prompt version `evidence_review_prompt_v1`.

## Lệnh chạy

```powershell
python -X utf8 scripts/evaluation/run_evidence_review.py --mode smoke
python -X utf8 scripts/evaluation/run_evidence_review.py --mode all
python -X utf8 scripts/evaluation/validate_evidence_review_runtime.py
```

`--mode smoke` dùng q-001, q-003 và q-012 để kiểm tra đường chạy. `--mode all`
chỉ ghi package cuối khi toàn bộ 40 output hợp lệ.

## Artifact

- Quyết định gốc đã đưa vào project:
  `docs/decisions/phase8_m2b_local_llm_decision_report.docx`.
- Output 40 câu:
  `evaluation/review/evidence_accept_reject/ollama_llama32_3b_reviews_v1.jsonl`.
- Validation từng câu:
  `evidence_review_runtime_validation.csv`.
- Runtime identity, config và SHA-256:
  `evidence_review_runtime_manifest.json`.
- Smoke evidence:
  `evidence_review_runtime_smoke_outputs.jsonl` và
  `evidence_review_runtime_smoke_validation.csv`.

