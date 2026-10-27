# Gatecheck

**Is your repo ready for a coding agent?** Gatecheck scans a repository and scores how
well Claude Code, Codex, Cursor or any agent can actually work in it — and it checks
that the commands and paths your `AGENTS.md` promises still exist.

**[Run it on your repo →](https://github.com/Edmarkavs/gatecheck/issues/new?title=scan%3A%20owner%2Frepo)** · **[See the data](docs/reports/stats.json)**

## Why

We scanned 300 public repos that already ship `SKILL.md` / `AGENTS.md` files:

| Finding | Value |
|---|---|
| Claims (commands, paths) that point at nothing | **39%** of 1,858 checked |
| Repos with no context file at all | **45%** |
| Repos scoring D or F | **54%** |
| Median score | 51.7 / 100 |

Stars are unrelated to readiness. The most-starred skills collection in the sample
scores 14/100: no context file, no CI, no lockfile.

## Quick start

```bash
python scanner/scan.py owner/repo            # one repo, writes HTML + JSON to out/
python scanner/scan.py --file=repos.txt --csv=corpus.csv --stats=stats.json
python scanner/scan.py --local=.             # scan the current directory, offline
```

Free scan by issue: open an issue titled `scan: owner/repo`. A GitHub Action scans it
and comments the report; the HTML is published under `docs/reports/`.

## In CI

```yaml
- uses: actions/checkout@v4
- uses: Edmarkavs/gatecheck@main
  with:
    fail-under: 70
```

## Signals (100 points)

| Signal | Pts | Checks |
|---|---|---|
| Context tells the truth | 20 | Every command and path in the context file exists |
| Context file present | 15 | AGENTS.md / CLAUDE.md / GEMINI.md / .cursorrules at root |
| Context budget | 12 | Under 8k chars read · over 15k truncated |
| Skill frontmatter | 12 | Valid `name` + `description` in each SKILL.md |
| Skill triggers | 10 | Description says *when* to use it |
| Skill references | 8 | No links to deleted `references/*.md` |
| Context freshness | 8 | Days since last edit, 90-day cliff |
| Execution guardrails | 8 | `curl \| bash`, `rm -rf /`, `allowed-tools: *` |
| Repo hygiene | 7 | CI, lockfile, tests, leaked secrets |

## Design constraints

- **Deterministic.** Same repo in, same score out. Safe to gate merges on.
- **No execution.** Files are read, never run. No `npm install`, no test suite.
- **No model calls.** Zero inference cost per scan.
- **Explainable.** Every losing point has a one-line reason in the report.

## Licence

MIT.
