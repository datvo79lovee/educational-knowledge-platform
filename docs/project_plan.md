# Educational Knowledge Platform — Project Plan

## Goal

Build a data engineering pipeline that collects educational content from MIT OpenCourseWare and makes it searchable through semantic retrieval.

## Architecture

```text
YouTube Data API
  -> Bronze video and metadata JSONL
  -> validation and deduplication
  -> Silver video metadata
  -> PostgreSQL
  -> transcript acquisition and checkpointing
  -> Bronze transcript JSONL
  -> Silver cleaned transcripts
  -> semantic chunks
  -> embeddings and vector database
  -> Semantic Search API
```

## Phase 1 — Foundation

- [x] PostgreSQL setup and connection
- [x] Schema and ERD design
- [x] Project structure and documentation

## Phase 2 — Video Metadata Ingestion

- [x] YouTube Data API integration
- [x] Channel and uploads playlist discovery
- [x] Playlist pagination
- [x] Collect 8,021 playlist video records
- [x] Retrieve 8,021 raw video metadata records
- [x] Validate, deduplicate, and normalize metadata
- [x] Produce 8,021 Silver video records
- [x] Load curated sources and videos into PostgreSQL
- [x] Validate the PostgreSQL load

## Phase 3 — Transcript Ingestion

- [x] Build a resumable transcript ingestion pipeline
- [x] Add append-only status checkpointing
- [x] Classify permanent, retryable, and blocking failures
- [x] Collect 290 transcripts for the MVP corpus
- [x] Reconcile successful payloads with checkpoint status
- [x] Freeze the MIT 6.0001 Fall 2016 target manifest with 38 videos
- [x] Collect all 38 target transcripts, including 34 new Bronze payloads
- [x] Validate 324 unique Bronze payloads with a PostgreSQL dry run
- [ ] Load the 34 new target transcripts into PostgreSQL
- [ ] Verify the committed PostgreSQL load and target-corpus coverage

## Phase 4 — Knowledge Processing

- [ ] Define the Silver transcript schema for the MIT 6.0001 corpus
- [ ] Clean and normalize transcript text
- [ ] Produce Silver transcript records
- [ ] Generate semantic chunks
- [ ] Validate chunk quality and lineage

## Phase 5 — Knowledge Retrieval

- [ ] Generate embeddings
- [ ] Load embeddings into a vector database
- [ ] Build the Semantic Search API
- [ ] Evaluate retrieval quality

## Current Status

Metadata ingestion is complete. Bronze contains 324 unique transcript payloads.
The MIT 6.0001 Fall 2016 target corpus has complete transcript coverage at 38/38:
4 payloads existed before targeted acquisition and 34 were newly collected.

A PostgreSQL dry run validated all 324 payloads. PostgreSQL still contains 290
transcripts, and the loader is expected to insert exactly 34 new rows. The next
step is to perform and verify that committed load before designing the Silver
transcript schema.

## State Ownership

- `data/bronze/transcripts_raw.jsonl` is the source of truth for successful transcript payloads.
- `data/bronze/transcripts_checkpoint.jsonl` is the source of truth for the latest processing status.
- Pipeline startup reconciles both sources and warns when a success checkpoint has no matching payload or a payload has no matching success checkpoint.
