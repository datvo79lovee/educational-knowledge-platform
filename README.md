# Educational Knowledge Platform

A Data Engineering + NLP/RAG system built on the 38-video **MIT 6.0001 Fall 2016**
corpus. It turns YouTube transcripts into a traceable Bronze → Silver → Gold pipeline,
an exact Dense retrieval index, and a grounded local-answer API that cites the exact
lecture timestamp it used — or abstains when the evidence is not sufficient.

Everything runs locally. No cloud, no external API at serving time.

## Architecture

```text
  INGESTION                    PROCESSING                   INDEXING
┌──────────────┐          ┌──────────────────┐         ┌──────────────────┐
│ YouTube Data │  Bronze  │ Silver: cleaned  │  Gold   │ MiniLM-L6-v2     │
│ API +        ├─────────►│ transcripts      ├────────►│ 861 × 384 float32│
│ transcripts  │  (raw)   │ Gold: 861 chunks │         │ exact cosine     │
└──────────────┘          └──────────────────┘         └────────┬─────────┘
       │                           │                            │
       └── lineage · SHA-256 · JSON Schema · checkpoint/resume ──┘
                                                                │
  SERVING                                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  POST /search  ──►  Dense Retrieval Top 3            (no model call)     │
│                                                                          │
│  POST /answer  ──►  [vi] literal translator ──► retrieval_query          │
│                     Dense Top 3                                          │
│                     G0 generator (Ollama · llama3.2:3b)                  │
│                     raw output → normalization → strict Pydantic         │
│                     application-owned citation mapping                   │
│                     ──► answer + citations   OR   abstain                │
│                                                                          │
│  GET  /        ──►  bounded local web demo (static HTML/CSS/JS)          │
└─────────────────────────────────────────────────────────────────────────┘
```

**The model never creates a citation.** It may only select chunk IDs from the exact
Dense Top 3; application code maps those IDs to canonical video URLs and timestamps.
An `answer` requires non-empty text plus 1–3 unique Top-3 IDs. An `abstain` requires
`answer=null` and no supporting IDs — enforced by a strict Pydantic contract, not by
convention.

For a Vietnamese request the runtime keeps `original_query`, translates it to a
literal English `retrieval_query`, retrieves the same Dense Top 3, then asks G0 to
answer in Vietnamese. Translation is **fail-closed**: an unavailable or invalid
translator never falls back to Vietnamese retrieval.

See [docs/architecture.md](docs/architecture.md) for the full canonical description.

## Path A — Run the included demo (default)

This is the default serving path intended for a fresh clone. It serves the committed canonical
artifacts and the bounded local web demo; it does **not** rebuild the data pipeline.

### System requirements

- Python 3.12
- [Ollama](https://ollama.com) — needed only for `/answer` and the demo's Ask button
- Network access is needed once to bootstrap the pinned query encoder and pull the
  Ollama tag, unless both are already present in local caches.
- Additional local disk is needed for the Ollama model and encoder cache. This
  repository does not claim a measured minimum RAM, GPU or disk configuration.
- PostgreSQL, YouTube credentials and the raw data lake are **not** needed for Path A.

The repository already ships the three canonical serving artifacts (Gold chunks,
embeddings, index metadata), so **no pipeline rebuild is required to serve**.

### 1. Install

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell;  source .venv/bin/activate on POSIX
pip install -r requirements.txt
```

### 2. Bootstrap the pinned query encoder

```bash
python -X utf8 scripts/bootstrap_query_encoder.py
```

Downloads the exact MiniLM revision recorded in the index manifest, verifies its
commit hash, and proves a second local-only load works. The API itself never
downloads a model at startup.

### 3. Pull the generator tag; runtime verifies the exact model identity

```bash
ollama pull llama3.2:3b
```

Canonical local-model identity:

```text
tag: llama3.2:3b
expected digest: a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72
```

`ollama pull` makes the tag available. Before its first model call, the runtime reads
the local Ollama model list and compares the full digest above; a mismatch fails
closed. It does not silently use another build with the same tag.

### 4. Start the API + demo

```bash
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

Startup verifies the SHA-256 of Gold, embeddings and metadata, checks index/metadata
alignment, and pins the encoder revision. **It refuses to start if anything drifted.**

Wait for this line before opening a browser:

```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Keep this terminal open — the server dies with it. Use a second terminal for anything
else.

### 5. Open the demo

<http://127.0.0.1:8000/>

Type a question, pick **English** or **Tiếng Việt**, press Ask. You get either an
answer with clickable lecture citations, or an explicit *not enough evidence* state.

### 6. Or call the API directly

```bash
curl -X POST http://127.0.0.1:8000/answer -H "Content-Type: application/json" -d "{\"question\":\"How does a function return a value to the code that called it?\",\"answer_language\":\"en\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/search -H "Content-Type: application/json" -d "{\"query\":\"recursion\"}"
```

`/search` and `GET /` need **no** Ollama. Only `/answer` does.

### 7. Verify the install

```bash
pytest -q
```

```bash
python -X utf8 scripts/api/validate_search_api.py
```

The validator prints its result and leaves the clone unchanged by default. To keep
a JSON validation manifest, choose an explicit untracked output path:

```bash
python -X utf8 scripts/api/validate_search_api.py --output tmp/search_api_validation.json
```

```bash
python -X utf8 scripts/evaluation/validate_benchmark_manifest.py
```

All three run without Ollama. On a clean machine they are the fastest proof the clone
is intact.

## Models and pinned identities

This release validates one identity per runtime role. It does not advertise a family
of interchangeable “supported models”. Using a different model requires a code and
evaluation change; its behavior is not covered by the frozen evidence.

| Component | Canonical identity | Purpose | Status |
|---|---|---|---|
| Dense query encoder | `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Exact cosine query embeddings | Pinned to the canonical 861 × 384 index |
| Grounded-answer generator | `llama3.2:3b` at digest `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | English/ Vietnamese grounded answer or abstain | Pinned and evaluated; not production-ready |
| Vietnamese retrieval translator | Same `llama3.2:3b` tag and digest | Literal VI → EN retrieval adapter | Pinned runtime identity; literal-fidelity evaluation remains rejected with documented limitations |

The translator is an internal retrieval adapter. Its literal Vietnamese-to-English
translation fidelity remains rejected by the frozen M2 evaluation.

## Repository map

| Path | What it holds |
|---|---|
| [`src/`](src/) | Runtime + pipeline modules ([README](src/README.md)) |
| [`scripts/`](scripts/) | Operational and evaluation runners ([README](scripts/README.md)) |
| [`tests/`](tests/) | Automated contract tests ([README](tests/README.md)) |
| [`reports/`](reports/) | Frozen milestone evidence, one folder per milestone ([README](reports/README.md)) |
| [`evaluation/`](evaluation/) | Benchmark, ground truth and human-review artifacts ([README](evaluation/README.md)) |
| [`schemas/`](schemas/) | JSON Schema contracts ([README](schemas/README.md)) |
| [`docs/`](docs/) | Architecture, decisions, status, build log ([README](docs/README.md)) |
| [`sql/`](sql/) | PostgreSQL ingestion schema ([README](sql/README.md)) |
| [`data/`](data/) | Data lake; only canonical serving artifacts are tracked ([README](data/README.md)) |

## Evaluation, honestly reported

The major evaluation milestones reported below were pre-registered before execution,
with hashes pinned where required for inputs, runtime sources and analysis code.
Failed milestones are frozen as failures, not deleted.

**Grounded answer, English (Reliability V1 / G0)** — 40 human-approved benchmark
questions:

| Metric | Result |
|---|---:|
| Public runtime success | 40/40 |
| Decision accuracy | 23/37 (62.16%) |
| False abstain | 11/21 evidence-sufficient |
| False answer | 3/16 evidence-insufficient |
| Strict end-to-end success | 17/37 (45.95%) |

**Multilingual retrieval translation (M2)** — measured on 20 paired intents:

| Milestone | Question | Outcome |
|---|---|---|
| M2 | Does the machine translator preserve retrieval fidelity? | **FAIL** — 10/20 semantic drift, Recall@3 0.55 vs 0.70. Translator rejected |

The single most useful finding: **retrieval metrics can be blind to semantic
translation failure.** In M2, `q-039` lost the entire "white-box" half of its question
yet kept a perfect 3/3 Top-3 overlap and zero rank change. A metric gate alone would
have accepted it; the human semantic gate caught it.

## Limitations — read before judging the numbers

- **Not production-ready.** No milestone claims otherwise, and the frozen manifests
  forbid the claim explicitly.
- **Translator still rejected.** M2's literal Vietnamese-to-English translation did
  not meet the frozen fidelity and retrieval gates.
- **Retrieval ceiling.** Recall@3 is 0.743, so ~26% of answerable questions cannot be
  answered correctly no matter how good the generator is.

Full measured basis: [docs/status/CURRENT_STATUS.md](docs/status/CURRENT_STATUS.md)
and [docs/decisions/CANONICAL_RUNTIME_DECISIONS.md](docs/decisions/CANONICAL_RUNTIME_DECISIONS.md).

## Troubleshooting

| Symptom | What it means | Safe next step |
|---|---|---|
| Bootstrap cannot load the query encoder | The exact MiniLM revision is not available locally yet, or the bootstrap could not download it. | Check network access and rerun `python -X utf8 scripts/bootstrap_query_encoder.py`. |
| `/search` is available but `/answer` returns `503` | Dense serving does not need Ollama; grounded answering does. | Start Ollama, pull `llama3.2:3b`, then retry. The runtime checks the exact digest before the first model call. |
| `/answer` rejects the local model | The local tag does not have the canonical digest listed above. | Do not substitute another build with the same tag; refresh the canonical tag and let the runtime verify it again. |
| The demo says “not enough evidence” | The system abstained under its strict answer/evidence contract. | Treat it as an abstention, not as a prompt to fabricate an answer. |
| Pipeline commands require credentials or PostgreSQL | You are using Path B rather than the included serving path. | Follow the optional rebuild prerequisites below. |

## Path B — Rebuild the data pipeline (advanced / optional)

Serving needs none of this. A Bronze → Silver → Gold rebuild additionally needs the
raw data lake, network access, YouTube credentials, PostgreSQL and pipeline-specific
dependencies. A clean clone has **not** been presented as proof of this full rebuild
path.

```bash
pip install -r requirements-pipeline.txt
cp .env.example .env        # then fill in your own credentials; never commit .env
```

The committed `embeddings.npy` is authoritative. A byte-identical rebuild requires the
exact Python, NumPy, PyTorch, Transformers and Sentence Transformers versions pinned
in `requirements.txt` and `data/indexes/mit_60001/manifest.json`. Under
other versions, keep the committed artifact.

## Future improvements

These are evidence-driven next steps, not claims that the current local demo is
production-ready:

- Evaluate on a larger unseen English set and a separate Vietnamese holdout set.
- Improve and re-evaluate Vietnamese translation fidelity without tuning to the
  observed reused intents.
- Raise retrieval Recall@3 before attributing failures solely to generation.
- Compare stronger local generators and calibrate abstention under a pre-registered
  protocol.
- Add multi-reviewer evaluation and agreement measurement.
- Make optional pipeline orchestration and clean-clone validation simpler and more
  reproducible.
- Add CI smoke validation for the bounded local serving/demo contract.
