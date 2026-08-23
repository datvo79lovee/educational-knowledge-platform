# Evaluation workspace

`evaluation/mit_60001/` contains the canonical MIT 6.0001 benchmark:

```text
evaluation/mit_60001/
├── evaluation_questions.jsonl
└── benchmark_manifest.json
```

Run the compact provenance validator with:

```powershell
python -X utf8 scripts/evaluation/validate_benchmark_manifest.py
```

The canonical benchmark has 35 answerable questions, 5 intentional out-of-scope
questions, and 57 Ground Truth time ranges. Historical candidate/review workbooks
were removed after this manifest was validated; the final JSONL remains the source
of truth for benchmark labels.

`evaluation/review/grounded_answer/` retains only the canonical Reliability V1
human-judgment CSV used by the final G0 result.
