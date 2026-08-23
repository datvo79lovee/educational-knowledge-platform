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

Prerequisites: Python 3.12, Ollama, and the canonical local model.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.2:3b
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

In a second terminal, validate the retrieval API or call it directly:

```powershell
python -X utf8 scripts/api/validate_search_api.py
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search `
  -ContentType 'application/json' -Body '{"query":"What is recursion?"}'
```

The grounded-answer endpoint additionally requires the local Ollama service to be
running:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/answer `
  -ContentType 'application/json' -Body '{"question":"What is recursion?"}'
```

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

The next research phase is multilingual retrieval baseline evaluation, not further
generator prompt tuning.
