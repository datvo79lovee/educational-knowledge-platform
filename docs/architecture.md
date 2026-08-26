# Canonical architecture

```text
YouTube API
   ↓
Bronze → Silver → Gold
   │
   ├─ lineage / SHA-256 hashes
   ├─ JSON Schema validation
   └─ checkpoint / resume
   ↓
Embedding / canonical Dense index
   ↓
Dense Retrieval (Top 3)
   ↓
Grounded Answer Generator — Ollama / llama3.2:3b
   ↓
Raw model output
   ↓
Application normalization
   ↓
Strict Pydantic validation
   ↓
Application-owned citation mapping
   ↓
API response: answer + citations, or abstain
```

The model never creates citation URLs or timestamps. It may choose only supporting
chunk IDs from the exact Dense Top 3; application code maps those IDs to canonical
metadata. An `answer` requires a non-empty answer and one to three unique Top-3 IDs.
An `abstain` requires a null answer and no supporting IDs.

## Multilingual Runtime V1

For a Vietnamese request, the runtime preserves `original_query`, uses the pinned
literal translator to create `retrieval_query`, retrieves the same Dense Top 3, then
asks G0 to answer in Vietnamese. Translation is fail-closed: an unavailable or
invalid translator response does not fall back to Vietnamese retrieval. English
requests retain the frozen `grounded_answer_prompt_v1` and make no translation call.

The canonical components are `dense_baseline_v1` and G0/Reliability V1. Retired
experiments are intentionally absent from the active architecture.

## Serving surface

```text
GET  /                → bounded local web demo (static HTML/CSS/JS)
GET  /static/*        → demo assets, served from disk; no CDN, no external asset
POST /search          → Dense Top 3 only; no model call, no Ollama dependency
POST /answer          → grounded answer or abstain; requires Ollama
GET  /videos/{id}     → canonical metadata for one of the 38 target videos
```

The demo page is a static client of the unchanged `/answer` contract. It adds no
retrieval, generation or evidence logic, is excluded from the OpenAPI schema, and
renders only `decision`, `answer` and application-owned `citations`. The API response
may include `original_query` and `retrieval_query`, but the bundled UI does not read
or render either field. Raw model output and normalization metadata are not public API
response fields. A test enforces the UI boundary by scanning the static assets.

Startup is fail-closed: the application verifies the SHA-256 of the canonical Gold
chunks, embeddings and index metadata, checks positional alignment between them, and
pins the query-encoder revision before accepting a request.
