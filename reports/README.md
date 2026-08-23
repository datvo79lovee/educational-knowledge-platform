# Canonical reports

Only final pipeline evidence is retained in `reports/`:

- `01_data_audit` through `09_embedding`: corpus, cleaning, canonical Gold and
  canonical Dense index evidence.
- `12_search_api`: validation of the Dense Top-3 Search API.
- `20_grounded_answer_runtime`: runtime contract and smoke-validation manifest.
- `25_grounded_answer_reliability_v1`: final G0/Reliability V1 metrics, results and
  manifest.

Deprecated retrieval and reviewer experiment reports were removed after their final
selection decisions were recorded in `docs/decisions/CANONICAL_RUNTIME_DECISIONS.md`.
