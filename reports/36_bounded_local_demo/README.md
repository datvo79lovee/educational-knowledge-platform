# Bounded local demo — M2 release remediation

## Status

`VALIDATED ON LOCAL RELEASE CANDIDATE`

This report freezes the M2 behavior check for the bounded local demo. It is not a
quality evaluation, a production-readiness claim, or a replacement for M2/M5.1/M5.3/
M6 evidence.

## Scope

- `GET /` and static JavaScript served by FastAPI.
- `POST /search` returns the unchanged Dense Top 3 contract.
- `GET /videos/{video_id}` returns canonical metadata.
- `POST /answer` accepts both `answer_language=en` and `answer_language=vi` only after
  local Ollama matches the canonical full digest.

The bundled UI sends only `question` and `answer_language`, and renders only
`decision`, `answer` and application-owned citations. The API may include
`original_query` and `retrieval_query`; the UI does not read or render them.

## Evidence

`demo_validation_manifest.json` records the exact source hashes, test result and only
response status/shape observations. It deliberately stores no generated answer text.

## Line-ending inventory — deferred

M2 only inventories these pre-existing worktree indications. It does not normalize or
rewrite them; `w/mixed` is a risk signal, not proof that a Git artifact hash is wrong.

| File | Git attribute expected | Current indication | Hash-sensitive | M2 action |
|---|---|---|---|---|
| `.gitignore` | LF | `w/mixed` | No | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `reports/01_data_audit/transcript_summary.csv` | LF | `w/mixed` | No | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `reports/01_data_audit/video_transcript_summary.csv` | LF | `w/mixed` | No | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `reports/03_playlist_mapping/playlists.csv` | LF | `w/mixed` | No | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `reports/35_multilingual_runtime_v1_m6/m6_human_review_worksheet_reviewed.csv` | LF | `w/mixed` | Yes — frozen review hash | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `src/grounded_answer/contracts.py` | LF | `w/mixed` | Yes — runtime source was pinned by milestone protocols | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `src/ingestion/fetch_transcripts.py` | LF | `w/mixed` | No serving-artifact hash | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
| `tests/grounded_answer/grounded_answer_runtime_test.py` | LF | `w/mixed` | No serving-artifact hash | `DEFER_TO_M5_CLEAN_CLONE_VALIDATION` |
