# Phase 8 — Evidence reviewer prompt experiment

## Mục tiêu

Experiment cô lập tác động của prompt trên cùng request package Dense Top 3 và
cùng local model `llama3.2:3b`. Runtime không đọc calibration, Ground Truth,
`expected_answer_points` hoặc `relevant_time_ranges`.

```text
E0  locked baseline: prompt V1 + Ollama 0.32.13
E1  current control: prompt V1 + Ollama 0.32.14
E2  candidate:       prompt V2 + Ollama 0.32.14
```

E1 tồn tại để không quy toàn bộ sai lệch giữa E0 và E2 cho prompt trong khi
phiên bản Ollama đã thay đổi.

## Prompt V2

Prompt V2 vẫn chỉ nhận question và Dense Top 3 nhưng siết điều kiện sufficiency:

- phải hỗ trợ toàn bộ các phần thiết yếu của câu hỏi;
- câu so sánh phải có evidence cho cả hai phía và sự khác biệt được hỏi;
- câu `why` phải có nguyên nhân, câu `how/what happens` phải có cơ chế/hành vi;
- evidence cùng chủ đề hoặc chỉ hỗ trợ một phần phải bị reject;
- `supporting_chunk_ids` chỉ chứa ID cần thiết, không lặp và không nằm ngoài Top 3.

## Kết quả M2 — chưa dùng Ground Truth

| Run | Prompt | Ollama | Accept | Reject | Failure |
|---|---|---:|---:|---:|---:|
| E0 locked baseline | V1 | 0.32.13 | 27 | 13 | 0 |
| E1 current control | V1 | 0.32.14 | 26 | 14 | 0 |
| E2 candidate | V2 | 0.32.14 | 30 | 10 | 0 |

So sánh cơ học:

| So sánh | Top 3 giữ nguyên | Decision đổi | Supporting IDs đổi |
|---|---:|---:|---:|
| E0 → E1 | 40/40 | 1/40 (`q-019`) | 1/40 (`q-019`) |
| E1 → E2 | 40/40 | 6/40 | 23/40 |

Sáu câu đổi decision giữa E1 và E2 là `q-001`, `q-009`, `q-014`, `q-019`,
`q-021`, `q-023`.

E2 accept nhiều hơn E1 dù prompt được viết chặt hơn. Đây chỉ là phân bố output,
không phải bằng chứng E2 tốt hơn hoặc xấu hơn. FAR, FRR, recall và evidence
entailment chỉ được tính trong M3.

## Validation

- Hai variant đều sinh đủ `40/40` response hợp lệ.
- `80/80` response giữ nguyên retrieval identity và Dense Top 3.
- Không có supporting ID ngoài Top 3.
- Request package hash giữ nguyên:
  `1cafc735ec5a40cf0179c017f064dd9cd3d187f0a4b90564d68680928e257a3e`.
- Model digest giữ nguyên:
  `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`.
- Validator độc lập: `passed`.
- Test evidence-review: `21 passed`.
- Ground Truth được đọc trong runtime/comparison: `false`.

## Artifact

- Prompt candidate: `src/evidence_review/prompts_v2.py`.
- Control output: `evaluation/review/evidence_accept_reject/experiments/prompt_v2/control_v1_reviews.jsonl`.
- Candidate output: `evaluation/review/evidence_accept_reject/experiments/prompt_v2/candidate_v2_reviews.jsonl`.
- Delta theo từng câu: `evaluation/review/evidence_accept_reject/experiments/prompt_v2/decision_deltas.csv`.
- Runtime/variant manifest: `prompt_experiment_manifest.json`.
- E0/E1/E2 comparison: `mechanical_comparison.json`.
- Per-question validation: `control_v1_validation.csv` và
  `candidate_v2_validation.csv`.
- Smoke evidence: `control_v1_smoke_*` và `candidate_v2_smoke_*`.

## Lệnh chạy lại

```powershell
python -m pytest tests/evidence_review -q
python -X utf8 scripts/evaluation/run_evidence_review_prompt_experiment.py --mode smoke
python -X utf8 scripts/evaluation/run_evidence_review_prompt_experiment.py --mode all
python -X utf8 scripts/evaluation/build_evidence_review_prompt_comparison.py
python -X utf8 scripts/evaluation/validate_evidence_review_prompt_experiment.py
```

## Ranh giới M2

M2 chỉ tạo và validate output experiment. Chưa tính accuracy/FAR/FRR, chưa human
review supporting chunks, chưa chọn V2 và chưa sinh grounded answer. Ba câu
`q-017`, `q-023`, `q-041` vẫn giữ trạng thái audit/exclusion của M3 baseline;
experiment này không sửa Ground Truth.
