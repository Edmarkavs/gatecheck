---
name: gatecheck
description: Use when you need to know whether a repository is ready for a coding agent, when an agent keeps guessing test commands or ignoring AGENTS.md, or before onboarding a repo to Claude Code, Codex or Cursor. Scores the repo 0-100 and lists what to fix first.
license: MIT
---

# Gatecheck

Deterministic readiness scan for a repository. Nine signals, no model calls, no code
execution. Use it before trusting a repo's `AGENTS.md`, or in CI to block regressions.

## When to use

- An agent keeps running the wrong test command or invents files that don't exist.
- You inherited a repo with a 900-line `CLAUDE.md` nobody maintains.
- You are about to hand a repo to an agent and want a baseline score.

## Run it

```bash
python scanner/scan.py --local=.            # current directory, offline
python scanner/scan.py owner/repo           # public repo via the GitHub API
python scanner/scan.py --local=. --markdown # table for a PR comment
```

Exit artefacts: `out/<owner>__<repo>.html` (report) and `.json` (score + signals).

## Reading the result

- **80-100** — ready. Keep the context file fresh and under budget.
- **55-79** — works, but the agent will waste turns. Fix the top two failing signals.
- **0-54** — the agent is guessing. Usually a missing or stale context file.

The highest-leverage signal is *Context tells the truth* (20 pts): every command and
path your context file mentions must exist. See `references/signals.md` for the weights
and what each one measures.

## Rules

- Do not edit the score by deleting honest documentation; fix the repo instead.
- Never add a model call to make a signal "smarter" — determinism is the product.
