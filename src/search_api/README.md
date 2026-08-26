# `src/search_api/` — API and bounded local demo

## Endpoints

| Route | Needs Ollama | Purpose |
|---|---|---|
| `GET /` | no | Bounded local web demo page |
| `GET /static/*` | no | Demo assets, read from disk |
| `POST /search` | no | Dense Top 3 retrieval only |
| `POST /answer` | **yes** | Grounded answer or abstain |
| `GET /videos/{video_id}` | no | Canonical metadata for a target video |

## Fail-closed startup

`DenseSearchService.load()` runs before the first request and refuses to start if
anything drifted:

- SHA-256 of Gold chunks, embeddings and index metadata must match the index manifest
- Gold ↔ metadata ↔ vector rows must align positionally, one by one
- every vector must be finite and L2-normalized within tolerance
- the query encoder must load from local cache at the pinned revision, with matching
  dimension and max sequence length

A broken clone therefore fails loudly at boot instead of silently serving wrong
neighbours.

## The demo

`static/index.html`, `static/app.css`, `static/app.js` — plain HTML/CSS/JS. No
framework, no npm, no CDN, no external asset. The page is a static client of the
unchanged `/answer` contract.

It renders exactly three response fields: `decision`, `answer`, and application-owned
`citations`. The API response may include `original_query` and `retrieval_query`, but
the bundled UI deliberately does not read or display either field. Raw model output
and normalization metadata are not public API response fields.
`tests/search_api/search_api_validation_test.py` enforces this UI boundary with a
strict substring scan of the static assets.

Other demo behaviour worth knowing:

- The language selector maps directly to `answer_language=en|vi`. There is **no**
  language auto-detection.
- An `abstain` renders an explicit *not enough evidence* state. The page never
  fabricates an answer.
- API errors render fixed, non-leaking messages keyed by HTTP status. Server response
  bodies are never rendered.
- All server text is inserted with `textContent`, never as HTML.
- The page is excluded from the OpenAPI schema; it is not part of the API contract.

## Run

```bash
python -m uvicorn src.search_api.app:app --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000/>. Keep the terminal open — the server stops with it.
