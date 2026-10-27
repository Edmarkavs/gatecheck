# AGENTS.md

Gatecheck is a deterministic repo-readiness scanner for coding agents. It reads a
repository's tree, context files and skills and returns a 0-100 score. No LLM calls,
no code execution, no network access in local mode.

## Stack

- Python 3.10+ standard library only. No third-party runtime dependencies.
- Entry point: `scanner/scan.py` (single file, ~600 lines).
- Static site lives in `docs/` and is served by GitHub Pages from this repo.
- CI: `.github/workflows/scan.yml` (IssueOps scanner) and `ci.yml` (tests).

## Commands

```bash
python scanner/scan.py --local=.
python -m unittest discover -s tests -v
```

## Layout

- `scanner/scan.py` — scoring engine, nine signals, HTML/Markdown/JSON renderers.
- `docs/` — landing page, published reports in `docs/reports/`, corpus data.
- `tests/` — unit tests for the claim verifier and the scorer.
- `action.yml` — composite GitHub Action that wraps a local scan.

## Rules

- Never add a network call to local mode. `--local` must work offline and in CI.
- Never execute repository code. The scanner only reads files.
- Every signal must be explainable in one sentence in the report; no opaque scores.
- When you add a signal, update the weights so they still sum to 100.
- Public copy in `docs/index.html` must match `docs/reports/stats.json`. No invented numbers.
- Keep `scanner/scan.py` dependency-free: it ships inside a composite action.

## Gotchas

- On Windows the `pi`/`gh` shims can mis-resolve MSYS paths; pass `C:/...` style paths.
- The scanner caches remote API responses in `.cache/`; that directory is gitignored.
- `docs/reports/*.html` are generated artefacts. Regenerate, don't hand-edit.
