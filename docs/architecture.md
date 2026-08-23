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

The canonical components are `dense_baseline_v1` and G0/Reliability V1. Retired
experiments are intentionally absent from the active architecture.
