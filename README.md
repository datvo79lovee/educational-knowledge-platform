# Educational Knowledge Platform

## Overview

Educational Knowledge Platform is a personal Data Engineering project that collects educational content from YouTube and transforms it into a semantic-search-ready knowledge base.

The project follows a Medallion Architecture (Bronze, Silver, Gold). Bronze and PostgreSQL currently contain 324 MIT OpenCourseWare transcripts. The planned semantic-search MVP is scoped to the 38-video MIT 6.0001 Fall 2016 corpus.

## Architecture

```text
YouTube Data API
  -> Bronze JSONL (playlist/video IDs and raw metadata)
  -> validation and deduplication
  -> Silver video metadata
  -> PostgreSQL (sources and videos)
  -> eligible video queue
  -> resumable transcript acquisition and checkpointing
  -> Bronze transcript JSONL
  -> clean and normalize
  -> Silver transcripts
  -> canonical Gold chunks
  -> embeddings and exact local vector index
  -> Dense Top 3 Search API
  -> Grounded Answer Generator (next phase)
       -> answer with chunk/video/timestamp citations
       -> or abstain when Top 3 is insufficient
```

Transcript JSONL is the source of truth for successful payloads. The append-only checkpoint is the source of truth for processing status and supports safe resume after interruption.

## Current Progress

### Completed

- Collected 8,021 MIT OpenCourseWare videos
- Retrieved and normalized video metadata
- Loaded curated metadata into PostgreSQL
- Implemented data-quality validation
- Built resumable transcript ingestion with checkpointing
- Collected 324 transcripts and completed 38/38 coverage for the MIT 6.0001 target corpus
- Built lossless Silver transcripts for 38/38 target videos and 12,518 segments
- Selected and promoted 861 canonical Gold chunks
- Built and validated the 861 x 384 exact dense embedding index
- Completed Dense, BM25, RRF, and Cross-Encoder comparison; selected Dense baseline
- Canonicalized 40 approved evaluation questions
- Implemented and validated the retrieval-only Dense Top 3 Search API
- Evaluated and deprecated a standalone Evidence Reviewer after its frozen quality
  gate was not achieved; preserved all experiment artifacts

### In Progress

- Grounded answer generation with citations
- Generator-level abstention for insufficient evidence
- End-to-end groundedness, citation, and out-of-scope abstention evaluation

## Dataset Snapshot

| Dataset | Records |
| --- | ---: |
| Playlist video raw | 8,021 |
| Video metadata raw | 8,021 |
| Video metadata Silver | 8,021 |
| Successful transcripts | 324 |
| Transcript checkpoint records | 338 |
| Videos represented in checkpoints | 336 |

Observed checkpoint records: 324 `success`, 5 `no_transcript`, 5 `transcripts_disabled`, 2 `fetch_failed`, and 2 `ip_blocked`.

## Tech Stack

- Python
- PostgreSQL
- SQLAlchemy
- Pandas
- YouTube Data API
- youtube-transcript-api
- NumPy exact cosine index
- sentence-transformers
- FastAPI and Uvicorn

## Project Structure

```text
data/
    bronze/
    silver/
    gold/

src/
    ingestion/
    processing/
    embedding/
    database/
    quality/
    search_api/
```

## Retrieval/Search API

The current API is retrieval-only. It returns Dense Top 3 evidence from the locked
MIT 6.0001 corpus; it does not answer the question, accept/reject evidence, or
abstain on out-of-scope questions.

The final runtime architecture will not call a standalone Evidence Reviewer.
Controlled V1, V2, and A1 experiments were preserved for audit, but the component
was removed from the active path after it failed to provide reliable discrimination.
The Grounded Answer Generator will use only Dense Top 3 and will either return an
answer with chunk/video/timestamp citations or abstain when evidence is insufficient.

```powershell
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
python -X utf8 scripts/api/validate_search_api.py
python -X utf8 scripts/api/verify_search_api_cross_process.py
```

Endpoints:

```text
POST /search
GET /videos/{video_id}
```

The API reproduces the locked retriever's Top 3 IDs for 35/35 answerable benchmark
questions. This is implementation fidelity, not retrieval accuracy. The retriever's
benchmark Recall@3 remains `0.742857143`; therefore 35/35 API-to-baseline matches do
not mean that all 35 questions have correct evidence in Top 3.

See [the MIT 6.0001 implementation plan](docs/plans/MIT_60001_IMPLEMENTATION_PLAN.md)
for completed phases and upcoming work.
