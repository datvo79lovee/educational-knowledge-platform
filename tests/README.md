# `tests/` — automated contract tests

```bash
pytest -q
```

No Ollama, no network and no encoder download are required. `pytest.ini` limits
collection to this directory.

## Layout

| Path | What it locks |
|---|---|
| `search_api/` | Search contracts, fail-closed startup validation, demo route/static serving, and the demo diagnostic-leak guard |
| `grounded_answer/` | Answer/abstain contract shape, normalization behaviour, frozen English prompt hash, and the frozen report-20 fixtures |
| `multilingual/` | Fresh-process import-order guard for the active Vietnamese runtime branch |

## What these tests are for

They are focused runtime and API contract tests, not UI or model-quality tests.
Representative examples:

- client-supplied evidence is rejected and application-owned citations remain ordered
- the Vietnamese branch fails closed when its translator is unavailable
- the Dense Search API rejects incompatible index artifacts before serving requests
- a fresh interpreter can import the Vietnamese and grounded-answer modules in either
  order without a circular import

## Two conventions to know

**Subprocess for import-order tests.** `multilingual/import_order_test.py` spawns a
fresh interpreter. Inside a warm pytest process the import graph is already resolved,
so an in-process check would pass even while a circular import exists.

Historical milestone protocol tests were retired from the public test suite during
repository simplification. Their reports and runners are retained separately until a
later cleanup batch; they are not part of the current Crawl → Web runtime contract.
