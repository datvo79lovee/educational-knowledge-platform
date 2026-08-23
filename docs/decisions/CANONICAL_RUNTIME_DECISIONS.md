# Canonical runtime decisions

## Retrieval

`dense_baseline_v1` is the canonical retriever for the MIT 6.0001 corpus. It uses
the promoted canonical Gold chunks, the 384-dimensional exact Dense index, and
returns Top 3 evidence. BM25, Hybrid RRF, and Cross-Encoder were evaluated during
development but were not selected and are not retained as active repository
components.

## Grounded answer generation

`Reliability V1 / G0` is the canonical generator configuration:

```text
Dense Top 3 → llama3.2:3b → deterministic normalization → Pydantic validation
```

The application, rather than the model, creates citation URLs and timestamps from
the selected canonical chunk IDs. The final Reliability V1 results are retained in
`reports/25_grounded_answer_reliability_v1/` and its canonical human judgments are
in `evaluation/review/grounded_answer/grounded_answer_reliability_v1_human_review_canonical.csv`.

## Retired components

The standalone Evidence Reviewer and the G1 generator prompt experiment were
retired after evaluation. Their detailed development artifacts were intentionally
removed during repository cleanup; Git history records the former experiments.

## Limitation

G0 is a measured baseline, not a production-ready quality claim. Its final metrics
are descriptive in-sample results; the next open research task is multilingual
retrieval baseline evaluation.
