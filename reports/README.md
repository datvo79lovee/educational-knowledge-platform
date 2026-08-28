# Canonical reports

Only final pipeline evidence is retained in `reports/`:

- `01_data_audit` through `09_embedding`: corpus, cleaning, canonical Gold and
  canonical Dense index evidence.
- `12_search_api`: validation of the Dense Top-3 Search API.
- `20_grounded_answer_runtime`: runtime contract and smoke-validation manifest.
- `25_grounded_answer_reliability_v1`: final G0/Reliability V1 metrics, results and
  manifest.
- `26_multilingual_benchmark_preparation` through
  `28_multilingual_retrieval_evaluation`: frozen paired EN–VI retrieval baseline.
- `29_repository_reproducibility`: clean-clone reproducibility evidence.
- `30_multilingual_runtime_v1_m2`: frozen literal Vietnamese-to-English translation
  measurement.
- `36_bounded_local_demo`: source-pinned M2 validation of the bounded local demo.

Historical reports remain because their frozen manifests and decisions are provenance;
they are not all active runtime components. Active runtime selection is recorded in
`docs/decisions/CANONICAL_RUNTIME_DECISIONS.md`.
