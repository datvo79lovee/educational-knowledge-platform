# Machine-readable contracts

This folder contains versioned JSON Schemas for canonical pipeline and runtime
artifacts: Silver transcripts, Gold chunks, evaluation questions, embeddings, Dense
Search API, Grounded Answer API/runtime, and the compact benchmark manifest.

Schemas validate shape and types. Pipeline validators additionally check hashes,
coverage, ordering and cross-record invariants.

Key contracts:

- `chunking_evaluation_question_v1.schema.json`: canonical Ground Truth question.
- `benchmark_manifest_v1.schema.json`: compact benchmark provenance/counts/hash.
- `search_api_v1.schema.json`: retrieval-only `/search` contract.
- `grounded_answer_model_output_v1.schema.json` and
  `grounded_answer_api_v1.schema.json`: model and public `/answer` contracts.
