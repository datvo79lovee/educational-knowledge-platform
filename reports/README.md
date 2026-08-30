# Canonical reports

Only final pipeline evidence is retained in `reports/`:

- `01_data_audit` through `07_cleaning`: corpus, cleaning and canonical Silver
  evidence.
- `12_search_api`: validation of the Dense Top-3 Search API.
- `20_grounded_answer_runtime`: runtime contract and smoke-validation manifest.
- `25_grounded_answer_reliability_v1`: final G0/Reliability V1 metrics, results and
  manifest.
- `36_bounded_local_demo`: source-pinned validation of the bounded local demo.

Historical reports remain because their frozen manifests and decisions are provenance;
they are not all active runtime components. Active runtime selection is recorded in
`docs/decisions/CANONICAL_RUNTIME_DECISIONS.md`.
