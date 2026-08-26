# `sql/` — PostgreSQL ingestion schema

`schema.sql` defines the relational store used during **ingestion and auditing**:
`sources`, `videos`, `transcripts`, `chunks`.

## Not in the serving path

The API does not read PostgreSQL. `DenseSearchService` loads the canonical Gold chunks
and index metadata directly from `data/gold/` and `data/indexes/`, verified by SHA-256
at startup. PostgreSQL exists for pipeline ingestion and corpus auditing only, and the
serving stack has no database dependency.

This is a deliberate architectural seam, stated here so nobody has to infer it.

## Known gaps

Kept honest rather than quietly fixed, because changing them would rewrite pipeline
history that the reports depend on:

- `chunks.chunk_id` is `SERIAL` (integer), while the Gold contract uses a string
  `chunk_id` such as `nykOeWgQcHM:semantic_cosine_wp240_v1:6`. The two layers use
  different keys for the same entity.
- There is no `UNIQUE(video_id, language)` on `transcripts` and no natural key on
  `chunks`, so idempotency is enforced by the loader scripts rather than by the schema.
- There is no `pipeline_runs` table; run identity lives in the JSON manifests under
  `reports/`.

## Use

```bash
psql -f sql/schema.sql
```

Loaders live in `src/database/`. They need `.env` credentials and the raw data lake;
see the root README section on rebuilding the pipeline.
