# Repository reproducibility milestone

## Kết quả

Candidate repository snapshot đã PASS clean-room validation từ base commit
`0657d1a`. Snapshot không có `.git`, chứa đúng approved working-tree delta và bắt
đầu với Hugging Face cache rỗng. Agent chưa stage, commit hoặc push; actual remote
fresh clone chỉ có thể được kiểm tra sau khi user commit các file trong milestone.

Ba canonical serving artifacts được đưa ra khỏi ignore policy:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `data/gold/mit_60001/chunks.jsonl` | 1.289.944 | `c03abf002c29b784d191eb393670da27b80fed8e0e18798f113d7ff8b7daf432` |
| `data/indexes/mit_60001/embeddings.npy` | 1.322.624 | `3cf94fd32adf78e1e294d5562910f0d7144744a4c310de30f74f0084c80e56a7` |
| `data/indexes/mit_60001/metadata.jsonl` | 220.369 | `376faf54d90b6c4a30dc562aeba2127cbdd2953c243cd341bc288068dce4c7d7` |

`data/gold/mit_60001/experiments/`, `samples/`, Bronze, Silver và các manual
DB/network probes vẫn bị ignore. `embeddings.npy` là authoritative committed
candidate; rebuild byte-identical chỉ được kỳ vọng dưới đúng versions trong index
manifest và pinned requirements.

## Bootstrap query encoder

`scripts/bootstrap_query_encoder.py` đọc repository/revision/dimension/max sequence
length từ canonical embedding manifest. Trong clean room, script đã:

1. tải đúng `sentence-transformers/all-MiniLM-L6-v2` revision
   `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` vào cache rỗng;
2. verify `_commit_hash`, dimension `384` và max sequence length `256`;
3. load lần hai bằng `local_files_only=True` và PASS.

Ollama không thuộc query-encoder bootstrap. Search startup và `POST /search` không
cần Ollama; `POST /answer` được kiểm tra riêng.

## Clean-room validation

### Bắt buộc, không cần Ollama

| Gate | Kết quả |
|---|---:|
| Query encoder download từ isolated empty cache | PASS |
| Query encoder local-only reload | PASS |
| Pytest | 28/28 PASS |
| Canonical benchmark manifest | 40 questions, 57 ranges, PASS |
| Search API approved queries | 40/40 PASS |
| Answerable Top-3 IDs | 35/35 match |
| Answerable Top-3 scores | 35/35 match |
| Repeated responses | 40/40 match |
| Citation rows | 120/120 PASS |
| HTTP/startup failure cases | 16/16 PASS |

Full Search validator chạy application lifespan thật qua ASGI HTTP, nên gate này
bao gồm startup hash validation và `POST /search`; nó không gọi translator,
generator hoặc Ollama.

### Phân tầng reproducibility

| Tầng | Chạy được từ fresh clone | Cần data lake local |
|---|---|---|
| Serving và contract | `pytest`, `validate_search_api.py`, `validate_benchmark_manifest.py`, startup và `POST /search` | Không |
| Pipeline/research rebuild | Không | Chunking validators, M1/M2/M3 multilingual rebuild/validation và mọi Bronze → Silver → Gold rebuild |

Fresh-clone claim của milestone này áp dụng cho canonical serving package. Bronze,
Silver và Gold experiment inputs vẫn local-only có chủ đích; các pipeline/research
validator đọc những input đó không thuộc fresh-clone gate.

### Tách riêng, có Ollama

Local pinned `llama3.2:3b` smoke validation PASS `2/2` requests: một answer, một
abstain, hai citations, hai model calls. Output chỉ được ghi vào simulation temp;
frozen report 20 trong repository không bị sửa.

## Line-ending finding

Lần snapshot đầu dùng Git archive làm frozen report CSV chuyển LF thành CRLF, khiến
test hash có kết quả `27 passed, 1 failed`. Đây là fresh-checkout risk thật trên
Windows khi `core.autocrlf=true`, không phải model/test instability.

`.gitattributes` mới đặt default `text=auto eol=lf` để mọi text artifact hiện tại và
tương lai có checkout bytes độc lập với `core.autocrlf`; `.npy`, `.png` và `.xlsx`
được đánh dấu binary. Các rule canonical tường minh được giữ để document contract.
Tracked blobs hiện tại không chứa CR nên policy không yêu cầu historical
renormalization. Sau khi áp dụng policy trong candidate snapshot, pytest và
benchmark hash validator đều PASS.

## Negative scope

Milestone không thêm CI, Docker, orchestrator, pipeline ledger, database migration,
logging/health endpoint, retrieval experiment, K-ablation, risk-coverage,
multilingual encoder hoặc Multilingual Runtime V1.

Machine-readable evidence nằm tại
`reports/29_repository_reproducibility/repository_reproducibility_manifest.json`.
