# `src/` — application modules

Two distinct layers live here. Only the first one is needed to serve.

## Serving runtime (needed to run the API and demo)

| Module | Role |
|---|---|
| `search_api/app.py` | FastAPI app: `/`, `/static`, `/search`, `/answer`, `/videos/{id}` |
| `search_api/service.py` | Dense retrieval over the canonical index; fail-closed startup verification |
| `search_api/contracts.py` | Pydantic contracts for the search surface |
| `search_api/static/` | Bounded local web demo ([README](search_api/README.md)) |
| `grounded_answer/service.py` | Orchestration: retrieval → one generation call → normalization → citation mapping |
| `grounded_answer/contracts.py` | Strict answer/abstain contract; the shape rules live here |
| `grounded_answer/prompts.py` | Frozen English prompt v1 and the Vietnamese prompt |
| `grounded_answer/provider.py` | Provider-neutral generation interface |
| `grounded_answer/ollama_provider.py` | Pinned local Ollama provider with digest verification |
| `multilingual/translation.py` | Fail-closed literal VI→EN translator for the Vietnamese branch |
| `utils/jsonl.py` | JSONL helpers |

These modules are **hash-pinned** by the frozen milestone pre-registrations in
`reports/3*/`. Changing one makes those milestones' runners refuse to run — that is
intended: a frozen measurement describes the runtime it was registered against.

## Pipeline modules (needed only to rebuild the data lake)

| Package | Role |
|---|---|
| `ingestion/` | YouTube Data API and transcript acquisition into Bronze |
| `processing/` | Bronze → Silver cleaning, chunking, deduplication |
| `quality/` | Validation and cross-checks between layers |
| `database/` | PostgreSQL loaders for sources, videos, transcripts, chunks |
| `embedding/` | Embedding generation and vector-store loading |
| `config.py` | Environment/configuration loading for the pipeline |

Most of these are standalone entry points run as `python -m src.<package>.<module>`,
not imported libraries. They require the raw data lake, PostgreSQL and API credentials
described in the root README.

## Boundary that matters

`grounded_answer/service.py` is where the model's freedom ends. The model may return
only chunk IDs drawn from the exact Dense Top 3 of that same request; application code
maps those IDs to canonical URLs and timestamps. No prompt, model or normalization
path can produce a citation.
