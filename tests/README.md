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
| `multilingual/` | Milestone runner protocols for M3–M6: hash verification, per-stage diagnostics, gate arithmetic, review lifecycle |

## What these tests are for

They are **protocol tests**, not UI or model-quality tests. They exist because this
repository's claims rest on pre-registrations and hashes, and a pinned hash that
nobody checks is documentation rather than enforcement. Representative examples:

- the frozen English prompt must still hash to `2b0a35d6…`, so a Vietnamese change
  cannot leak across branches
- a wrong analysis-code or runtime hash must stop a milestone runner **before** any
  model call, and must create no artifact
- a failed record must retain the diagnostics its milestone promised, per stage
- a gate must count every failure layer, not only the one under investigation
- `--verify-only` must neither create nor overwrite any result artifact

## Two conventions to know

**Subprocess for import-order tests.** `multilingual/import_order_test.py` spawns a
fresh interpreter. Inside a warm pytest process the import graph is already resolved,
so an in-process check would pass even while a circular import exists.

**Isolated lifecycle tests.** Tests about "artifact X does not exist yet" use
`tmp_path` and monkeypatched paths rather than inspecting the real repository. Earlier
versions asserted against real files and went red the moment a milestone legitimately
ran; the property being tested belongs to the function, not to the repository's
current state.

## Frozen milestone runners refuse to run

`scripts/evaluation/run_multilingual_runtime_v1_m3.py` and `…_m4.py` now exit with a
runtime-hash mismatch, because M5 changed a pinned prompt module. That is correct
behaviour and is asserted by tests. The positive verification path stays covered
through fixture copies with refreshed runtime hashes; no frozen artifact is modified.
