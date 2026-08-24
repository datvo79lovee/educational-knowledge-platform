# Educational Knowledge Platform

## Overview

Educational Knowledge Platform is a Data Engineering and NLP/RAG project built on
the 38-video MIT 6.0001 Fall 2016 corpus. It turns YouTube transcripts into a
traceable Bronze → Silver → Gold pipeline, an exact Dense retrieval index, and a
grounded local-answer API with application-owned citations.

## Canonical architecture

```text
YouTube API → Bronze → Silver → Gold
                       ↓
          lineage, hashes, schema validation, checkpoint/resume
                       ↓
             embedding / canonical index
                       ↓
               Dense Retrieval Top 3
                       ↓
     Grounded Answer Generator (Ollama / llama3.2:3b)
                       ↓
     normalization → strict Pydantic validation
                       ↓
        application-owned citations → API response
```

`POST /search` is retrieval-only. `POST /answer` uses the same Dense Top 3 and
returns either a grounded answer with canonical citations or an abstention. The
model may select chunk IDs only; application code maps those IDs to video URLs and
timestamps.

## Canonical decisions

- `dense_baseline_v1` is the selected retriever.
- `Reliability V1 / G0` is the canonical grounded-answer runtime.
- Runtime normalization is deliberate application behavior: it converts only an
  abstain literal to `null` and deduplicates valid Top-3 supporting IDs before the
  final Pydantic validation.
- The standalone Evidence Reviewer, BM25/Hybrid RRF, Cross-Encoder, and G1 prompt
  experiment are not part of this repository's active architecture.

See [canonical runtime decisions](docs/decisions/CANONICAL_RUNTIME_DECISIONS.md)
and [current status](docs/status/CURRENT_STATUS.md) for the measured basis and
known limitations.

## Quick start

Prerequisite for retrieval: Python 3.12. The repository includes the exact three
canonical serving artifacts (Gold chunks, embeddings, and index metadata); larger
Bronze/Silver data and Gold experiments remain local-only.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -X utf8 scripts/bootstrap_query_encoder.py
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

The bootstrap command downloads the exact MiniLM revision recorded by the index
manifest, verifies its commit hash, and proves that a second local-only load works.
The API never downloads a model during startup.

In a second terminal, validate the retrieval API or call it directly:

```powershell
python -X utf8 scripts/api/validate_search_api.py
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search `
  -ContentType 'application/json' -Body '{"query":"What is recursion?"}'
```

`POST /search`, its startup hash gate, the test suite, and the Search API validator
do not require Ollama. The grounded-answer endpoint additionally requires the local
Ollama service and pinned model:

```powershell
ollama pull llama3.2:3b
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/answer `
  -ContentType 'application/json' -Body '{"question":"What is recursion?"}'
```

The committed `embeddings.npy` is authoritative. A byte-identical rebuild requires
the Python, NumPy, PyTorch, Transformers, and Sentence Transformers versions pinned
in `requirements.txt` and `reports/09_embedding/embedding_index_manifest.json`;
under other versions, use the committed artifact instead of replacing it.

## Development and pipeline setup

```powershell
pip install -r requirements-dev.txt
pip install -r requirements-pipeline.txt
pytest
python -X utf8 scripts/evaluation/validate_benchmark_manifest.py
```

Copy `.env.example` to `.env` only when running ingestion or PostgreSQL pipeline
steps. Never commit `.env`.

## Evaluation snapshot

The canonical benchmark contains 40 human-approved questions: 35 answerable, 5
out-of-scope, and 57 Ground Truth time ranges. Its compact provenance and hashes
are locked in [benchmark_manifest.json](evaluation/mit_60001/benchmark_manifest.json).

Reliability V1/G0 is an evaluated baseline, not a production-readiness claim:

- Public runtime success: 40/40
- Decision accuracy: 23/37 (62.16%)
- False abstain: 11/21 evidence-sufficient questions
- False answer: 3/16 evidence-insufficient questions
- Strict end-to-end success: 17/37 (45.95%)

Phase 9 multilingual retrieval baseline M1-M4 is complete. The next planned
capability is Multilingual Runtime V1 (`VI → literal EN → Dense → G0 → VI answer`),
without expanded translation, BM25, RRF, or reranking. It is not implemented yet.

Repository reproducibility evidence is recorded in
[`reports/29_repository_reproducibility/`](reports/29_repository_reproducibility/).
