# Grounded Answer Generator — runtime

## Mục tiêu

Stage này triển khai active flow sau Dense retrieval:

```text
Question
  -> dense_baseline_v1 Top 3
  -> one-call Grounded Answer Generator
       -> answer + application-owned citations
       -> hoặc abstain
```

`POST /search` giữ nguyên retrieval-only contract. `POST /answer` tự gọi
`DenseSearchService`; client không được truyền evidence tùy ý.

## Runtime đã khóa

```text
Provider       : Ollama local
Model          : llama3.2:3b
Model digest   : a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72
Ollama version : 0.32.14
Temperature    : 0
Seed           : 42
num_ctx        : 4096
num_predict    : 512
Prompt         : grounded_answer_prompt_v1
Retrieval      : dense_baseline_v1, Top 3
```

Generator thực hiện đúng một model call cho mỗi request. Không gọi Evidence
Reviewer, không retry và không auto-repair output sai contract.

## Contract và citation provenance

Model chỉ trả:

```json
{
  "decision": "answer | abstain",
  "answer": "string | null",
  "supporting_chunk_ids": [],
  "reason": "short string"
}
```

Application từ chối duplicate ID, ID ngoài Top 3, answer không có supporting ID và
mọi abstain còn answer/evidence. `reason` chỉ là diagnostic nội bộ, không expose qua
public API.

Citation không do model sinh. Application map supporting IDs sang metadata của
chính Dense response, sắp theo retrieval rank rồi trả `video_url`, `start`, `end` và
`citation_url`.

## M2 validation

| Kiểm tra | Kết quả |
|---|---:|
| Runtime requests | 2/2 |
| Model calls | 2, đúng một call/request |
| Answer smoke | 1 |
| Abstain smoke | 1 |
| Citation mappings | 2/2 |
| Invalid contract cases bị từ chối | 5/5 |
| Active-runtime leakage scan | PASS |
| Auto-repair | Không |

Answer smoke dùng câu `What is an assertion used for in Python?`. Abstain smoke
dùng câu ngoài corpus về type hints trong FastAPI. Validator không đọc canonical
evaluation questions, expected answer points, answerable flags hoặc human labels.

## M3 baseline evaluation

M3 đã chạy 40 primary + 40 repeat bằng đúng frozen runtime. Primary là canonical;
repeat chỉ đo stability. Human review dùng 37 câu evaluable, giữ exclusion q-017,
q-023 và q-041.

| Metric | Kết quả |
|---|---:|
| Decision accuracy | 18/37 = 48,65% |
| Runtime failures | 8/37 = 21,62% |
| Answer precision | 9/10 = 90% |
| Answer recall | 9/21 = 42,86% |
| False abstain | 10/21 = 47,62% |
| Answer correctness | 9/10 = 90% |
| Completeness | 7/10 = 70% |
| Groundedness | 8/10 = 80% |
| Citation entailment | 16/17 = 94,12% |
| Strict end-to-end success | 13/37 = 35,14% |

Strict end-to-end gồm bốn strict grounded answers và chín correct abstentions, không
phải 13 answer hoàn hảo. M3 được freeze là `baseline_evaluated`; không có
pre-registered quality gate nên không kết luận pass, fail hoặc production-ready.

## Ranh giới và bước tiếp theo

Runtime implementation đã hoàn thành, nhưng reliability chưa đạt: tám request trả
HTTP 502 do structured response không hợp lệ. Ưu tiên tiếp theo là chẩn đoán timeout,
Ollama transport, schema parsing, context, server lifecycle và orchestration bằng
frozen outputs. Không đổi prompt/model và không rerun M3 để làm đẹp metric trước khi
hoàn thành reliability diagnosis và regression validation.
