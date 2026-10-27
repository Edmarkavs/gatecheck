# Signals and weights

| Key | Label | Weight | Passes when |
|---|---|---|---|
| `ctx_truth` | Context tells the truth | 20 | Every command and path in the context file resolves |
| `ctx_present` | Context file present | 15 | AGENTS.md / CLAUDE.md / GEMINI.md / .cursorrules at root |
| `ctx_budget` | Context budget | 12 | ≤ 8,000 chars; partial credit to 15,000 |
| `skill_fm` | Skill frontmatter | 12 | Each SKILL.md has `name` + `description` |
| `skill_desc` | Skill triggers | 10 | Description states *when* to use it |
| `skill_refs` | Skill references | 8 | Linked files inside the skill exist |
| `ctx_fresh` | Context freshness | 8 | Edited ≤ 30 days ago (partial to 90) |
| `guardrails` | Execution guardrails | 8 | No `curl \| bash`, `rm -rf /`, `allowed-tools: *` |
| `hygiene` | Repo hygiene | 7 | CI, lockfile, tests, no leaked secrets |

Weights sum to 100. Grades: A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, F below.

## Why truth is weighted highest

A context file that lies is worse than no context file: the agent confidently runs a
command that does not exist, then hallucinates the fix. Across 300 scanned repos, 39%
of 1,858 verified claims pointed at nothing.
