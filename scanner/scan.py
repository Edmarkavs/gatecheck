#!/usr/bin/env python3
"""Gatecheck scanner v2 — ¿puede un agente de código trabajar en este repo?

Señales (100 pts):
  ctx_present 15 · ctx_truth 20 · ctx_budget 12 · ctx_fresh 8
  skills_fm 12 · skills_desc 10 · skills_refs 8 · guardrails 8 · hygiene 7

ctx_truth es la señal propietaria: verifica que los comandos y rutas que el
archivo de contexto (AGENTS.md / CLAUDE.md) promete EXISTAN de verdad.

Uso:
  python scan.py owner/repo [owner/repo ...] [--out=DIR] [--csv=f.csv] [--stats=f.json]
  python scan.py --file repos.txt --csv=corpus.csv --stats=stats.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

GH = os.environ.get("GH_BIN", "gh")
ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)

IDEAL, HARD = 8_000, 15_000
CTX_NAMES = {"AGENTS.MD", "CLAUDE.MD", "AGENT.MD", "GEMINI.MD", ".CURSORRULES"}
SECRET_RX = re.compile(r"(sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|xox[bap]-[0-9A-Za-z-]{10,})")
DANGER_RX = re.compile(r"(curl[^\n|]{0,90}\|\s*(ba)?sh|wget[^\n|]{0,90}\|\s*(ba)?sh|rm\s+-rf\s+/(?![\w.])|chmod\s+777\s+/)")
TRIGGER_RX = re.compile(r"(use when|use this when|use for|triggers?|when the user|cuando el usuario|úsalo cuando)", re.I)
CMD_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
INLINE_CMD = re.compile(r"`([^`\n]{2,90})`")


def _cache_path(key: str) -> Path:
    return CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".json")


def cached(key: str, producer, ttl_h: float = 24.0):
    p = _cache_path(key)
    if p.exists():
        age_h = (datetime.now().timestamp() - p.stat().st_mtime) / 3600
        if age_h < ttl_h:
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    val = producer()
    try:
        p.write_text(json.dumps(val), encoding="utf-8")
    except Exception:
        pass
    return val


def sh(args: list[str]) -> str:
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip()[:200])
    return p.stdout


LOCAL_ROOT: Path | None = None  # --local=<dir>: lee del disco, sin GitHub API


def _local_paths(root: Path) -> list[str]:
    skip = {".git", "node_modules", ".cache", "out", "dist", "build", ".venv", "venv", "__pycache__", ".next"}
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".python")]
        rel = Path(dirpath).relative_to(root).as_posix()
        for f in filenames:
            out.append(f if rel == "." else f"{rel}/{f}")
    return out


def _local_gh(path: str):
    root = LOCAL_ROOT
    assert root is not None
    files = _local_paths(root)
    newest = max((root / f).stat().st_mtime for f in files) if files else datetime.now().timestamp()
    pushed = datetime.fromtimestamp(newest, timezone.utc).isoformat(timespec="seconds")
    if path.endswith("?recursive=1"):
        return {"tree": [{"path": f, "type": "blob"} for f in files]}
    if "/commits?path=" in path:
        target = root / path.split("/commits?path=", 1)[1].split("&")[0]
        mt = target.stat().st_mtime if target.exists() else newest
        return [{"commit": {"committer": {"date": datetime.fromtimestamp(mt, timezone.utc).isoformat(timespec="seconds")}}}]
    return {"stargazers_count": 0, "default_branch": "local", "pushed_at": pushed}


def gh_json(path: str, ttl_h: float = 12.0):
    if LOCAL_ROOT is not None:
        return _local_gh(path)
    return cached("gh:" + path, lambda: json.loads(sh([GH, "api", path])), ttl_h)


def raw(full: str, ref: str, path: str) -> str | None:
    if LOCAL_ROOT is not None:
        p = LOCAL_ROOT / path
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def get():
        url = f"https://raw.githubusercontent.com/{full}/{ref}/{path}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "gatecheck/2"}), timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            return None
    return cached(f"raw:{full}:{ref}:{path}", get)


@dataclass
class Signal:
    key: str
    label: str
    weight: int
    score: float
    detail: str

    @property
    def points(self) -> float:
        return round(self.weight * self.score, 1)


@dataclass
class Report:
    repo: str
    stars: int = 0
    pushed_at: str = ""
    files_scanned: int = 0
    skills: int = 0
    ctx_chars: int = 0
    ctx_days: int | None = None
    truth_ok: int = 0
    truth_fail: int = 0
    signals: list[Signal] = field(default_factory=list)
    error: str = ""

    @property
    def total(self) -> float:
        return round(sum(s.points for s in self.signals), 1) if self.signals else 0.0

    @property
    def grade(self) -> str:
        t = self.total
        return "A" if t >= 85 else "B" if t >= 70 else "C" if t >= 55 else "D" if t >= 40 else "F"

    def row(self) -> dict:
        return {
            "repo": self.repo, "score": self.total, "grade": self.grade, "stars": self.stars,
            "skills": self.skills, "ctx_chars": self.ctx_chars, "ctx_days": self.ctx_days,
            "truth_ok": self.truth_ok, "truth_fail": self.truth_fail,
            "files": self.files_scanned, "pushed_at": self.pushed_at[:10],
            **{f"sig_{s.key}": round(s.score, 2) for s in self.signals},
        }


def _norm(p: str) -> str:
    p = p[2:] if p.startswith("./") else p
    return p.lstrip("/").rstrip("/")


def check_claims(text: str, paths: set[str], full: str, ref: str) -> tuple[int, int, list[str]]:
    cmds: list[str] = []
    for block in CMD_FENCE.findall(text):
        for line in block.splitlines():
            line = line.strip().lstrip("$ ").strip()
            if line and not line.startswith("#"):
                cmds.append(line)
    cmds += [c.strip() for c in INLINE_CMD.findall(text)]

    ok = fail = 0
    notes: list[str] = []

    pkg: dict = {}
    if any(re.match(r"^(npm|pnpm|yarn|bun)\b", c) for c in cmds) and "package.json" in paths:
        try:
            pkg = json.loads(raw(full, ref, "package.json") or "{}")
        except Exception:
            pkg = {}
    scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}

    for c in cmds:
        c1 = c.split("&&")[0].split("|")[0].strip()
        if re.match(r"^npm (test|start)\b", c1):
            key = c1.split()[1]
            ok, fail = (ok + 1, fail) if key in scripts else (ok, fail + 1)
            if key not in scripts:
                notes.append(f"`npm {key}` sin script")
            continue
        m = re.match(r"^(?:npm run|pnpm|yarn|bun run|bun)\s+([A-Za-z0-9:_-]+)", c1)
        if m:
            name = m.group(1)
            if name in ("i", "install", "test", "add", "dlx", "x", "create"):
                continue
            if name in scripts:
                ok += 1
            else:
                fail += 1
                notes.append(f"script `{name}` no existe")
            continue
        m = re.match(r"^make\s+([A-Za-z0-9_.-]+)", c1)
        if m and "Makefile" in paths:
            mk = raw(full, ref, "Makefile") or ""
            if re.search(rf"^{re.escape(m.group(1))}\s*:", mk, re.M):
                ok += 1
            else:
                fail += 1
                notes.append(f"target make `{m.group(1)}` no existe")
            continue
        if re.match(r"^(pytest|python -m pytest|uv run pytest)\b", c1):
            if any(p in paths for p in ("pyproject.toml", "setup.py", "tox.ini")):
                ok += 1
            else:
                fail += 1
                notes.append("pytest sin proyecto Python")
            continue
        if re.match(r"^cargo\b", c1):
            ok, fail = (ok + 1, fail) if "Cargo.toml" in paths else (ok, fail + 1)
            continue
        if re.match(r"^go (test|build|run)\b", c1):
            ok, fail = (ok + 1, fail) if "go.mod" in paths else (ok, fail + 1)
            continue
        if re.match(r"^docker[ -]compose\b", c1):
            if any("compose.y" in p for p in paths):
                ok += 1
            else:
                fail += 1
                notes.append("compose file inexistente")
            continue

    for pth in set(re.findall(r"`((?:[\w.-]+/)+[\w.-]+/?|\.[\w.-]+/[\w./-]+)`", text)):
        clean = _norm(pth)
        if not clean or clean.startswith("http"):
            continue
        if clean in paths or any(x.startswith(clean + "/") for x in paths):
            ok += 1
        else:
            fail += 1
            notes.append(f"ruta `{pth}` no existe")
    return ok, fail, notes[:3]


def audit(full_name: str) -> Report:
    rep = Report(repo=full_name)
    try:
        meta = gh_json(f"repos/{full_name}")
        ref = meta.get("default_branch", "main")
        tree = gh_json(f"repos/{full_name}/git/trees/{ref}?recursive=1", ttl_h=6)
        paths_list = [n["path"] for n in tree.get("tree", []) if n.get("type") == "blob"]
        paths = set(paths_list)
        rep.stars = meta.get("stargazers_count", 0)
        rep.pushed_at = meta.get("pushed_at", "")
        rep.files_scanned = len(paths_list)
        if not paths_list:
            rep.error = "árbol vacío"
            return rep

        root_ctx = [p for p in paths_list if p.count("/") == 0 and p.upper() in CTX_NAMES]
        ctx_path = sorted(root_ctx, key=lambda p: (p.upper() not in ("AGENTS.MD", "CLAUDE.MD"), p))[0] if root_ctx else None
        ctx = raw(full_name, ref, ctx_path) if ctx_path else None

        rep.signals.append(Signal("ctx_present", "Context file", 15,
                                  1.0 if ctx else 0.0,
                                  f"{ctx_path} ({len(ctx)} chars)" if ctx else "no AGENTS.md / CLAUDE.md — the agent guesses"))
        rep.ctx_chars = len(ctx or "")

        if ctx:
            ok, fail, notes = check_claims(ctx, paths, full_name, ref)
            rep.truth_ok, rep.truth_fail = ok, fail
            tot = ok + fail
            sc = 0.5 if tot == 0 else ok / tot
            det = ("nothing verifiable" if tot == 0 else
                   f"{ok}/{tot} claims verified" + (f" — e.g. {notes[0]}" if notes else ""))
            rep.signals.append(Signal("ctx_truth", "Context tells the truth", 20, sc, det))
        else:
            rep.signals.append(Signal("ctx_truth", "Context tells the truth", 20, 0.0, "nothing to verify"))

        n = len(ctx or "")
        sc = 0.0 if n == 0 else (1.0 if n <= IDEAL else 0.6 if n <= HARD else 0.15)
        rep.signals.append(Signal("ctx_budget", "Context budget", 12, sc,
                                  f"{n} chars" + (" (ok)" if 0 < n <= IDEAL else f" (ideal <{IDEAL})" if n else "")))

        days = None
        if ctx_path:
            try:
                commits = gh_json(f"repos/{full_name}/commits?path={ctx_path}&per_page=1")
                if commits:
                    days = (datetime.now(timezone.utc) - datetime.fromisoformat(
                        commits[0]["commit"]["committer"]["date"].replace("Z", "+00:00"))).days
            except Exception:
                pass
        rep.ctx_days = days
        sc = 0.5 if days is None else 1.0 if days <= 30 else 0.6 if days <= 90 else 0.2
        rep.signals.append(Signal("ctx_fresh", "Context freshness", 8, sc,
                                  "unknown" if days is None else f"{days} days since last edit"))

        skills = [p for p in paths_list if p.split("/")[-1] == "SKILL.md" and "node_modules" not in p]
        rep.skills = len(skills)
        sample = skills[:20]
        if not sample:
            rep.signals += [Signal("skill_fm", "Skill frontmatter", 12, 0.0, "0 skills"),
                            Signal("skill_desc", "Skill triggers", 10, 0.0, "0 skills"),
                            Signal("skill_refs", "Skill references", 8, 0.0, "0 skills")]
        else:
            fm = desc = refs_ok = 0
            bad: list[str] = []
            for p in sample:
                t = raw(full_name, ref, p) or ""
                m = re.match(r"^---\s*\n(.*?)\n---", t[:1200], re.S)
                fmm = dict(re.findall(r"^([A-Za-z_-]+)\s*:\s*(.+)$", m.group(1), re.M)) if m else {}
                if fmm.get("name") and fmm.get("description"):
                    fm += 1
                d = (fmm.get("description") or "").strip()
                if d and TRIGGER_RX.search(d):
                    desc += 1
                elif d and len(d) <= 300:
                    desc += 0.5
                else:
                    bad.append(p)
                base = p.rsplit("/", 1)[0]
                linked = set(re.findall(r"\]\(([^)]+\.(?:md|py|sh|json|ya?ml|ts|js))\)", t))
                linked |= set(re.findall(r"(?<![\w/])((?:scripts|references|assets|templates)/[\w./-]+\.(?:md|py|sh|json|ya?ml|ts|js))", t))
                missing = [l for l in linked
                           if f"{base}/{_norm(l)}" not in paths and _norm(l) not in paths]
                refs_ok += 0 if missing else 1
            k = len(sample)
            rep.signals += [
                Signal("skill_fm", "Skill frontmatter", 12, fm / k, f"{fm}/{k} with name+description"),
                Signal("skill_desc", "Skill triggers", 10, desc / k,
                       f"{desc:.0f}/{k} with explicit trigger" + (f" — weak: {bad[0]}" if bad else "")),
                Signal("skill_refs", "Skill references", 8, refs_ok / k, f"{refs_ok}/{k} with no broken links"),
            ]

        risky = [p for p in paths_list if p.endswith((".sh", ".bash", ".ps1")) or p.split("/")[-1] == "SKILL.md"][:15]
        hits = [p for p in risky if DANGER_RX.search(raw(full_name, ref, p) or "")]
        wild = sum(1 for p in sample[:10] if re.search(r"allowed[-_]tools\s*:\s*(\*|[\"']?\*)", raw(full_name, ref, p) or ""))
        sc = max(0.0, 1.0 - 0.5 * len(hits) - 0.25 * wild)
        det = "no dangerous patterns" if not hits and not wild else f"{len(hits)} curl|bash/rm · {wild} allowed-tools:*"
        rep.signals.append(Signal("guardrails", "Execution guardrails", 8, sc, det))

        have_ci = any(p.startswith(".github/workflows/") for p in paths_list)
        lock = any(p in paths for p in ("package-lock.json", "pnpm-lock.yaml", "uv.lock", "poetry.lock", "Cargo.lock", "go.sum"))
        tests = any(re.search(r"(^|/)(tests?|spec|__tests__)/", p) for p in paths_list)
        leak = any(SECRET_RX.search(raw(full_name, ref, p) or "") for p in
                   [x for x in paths_list if x.split("/")[-1] in ("README.md", "AGENTS.md", "CLAUDE.md")][:4])
        rep.signals.append(Signal("hygiene", "Repo hygiene", 7, (have_ci + lock + tests + (not leak)) / 4,
                                  ("CI " if have_ci else "no CI ") + ("· lock " if lock else "· no lock ") +
                                  ("· tests" if tests else "· no tests") + ("· LEAK" if leak else "")))
        return rep
    except Exception as e:  # noqa: BLE001
        rep.error = str(e)[:160]
        return rep


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@REPO@@ — Agent Readiness @@SCORE@@/100</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#08090b;color:#e7e9ee;font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
background-image:radial-gradient(900px 500px at 12% -10%,rgba(80,120,255,.14),transparent 70%),radial-gradient(700px 400px at 95% 0%,rgba(0,220,160,.10),transparent 70%)}
.wrap{max-width:900px;margin:0 auto;padding:56px 24px 80px}
.top{display:flex;gap:8px;align-items:center;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#7c8496}
.dot{width:6px;height:6px;border-radius:50%;background:#2ee6a8;box-shadow:0 0 12px #2ee6a8}
h1{font-size:34px;line-height:1.15;margin:14px 0 6px;letter-spacing:-.02em}
.sub{color:#8b93a5;margin:0 0 34px}
.hero{display:flex;gap:28px;align-items:center;flex-wrap:wrap;background:linear-gradient(180deg,#11141a,#0d1015);
border:1px solid #1e232d;border-radius:18px;padding:26px 28px;margin-bottom:26px}
.num{font-size:74px;font-weight:800;letter-spacing:-.04em;line-height:.9}
.num small{font-size:22px;color:#5d6577;font-weight:500}
.badge{display:inline-flex;align-items:center;gap:8px;padding:7px 13px;border-radius:999px;font-size:13px;font-weight:600;
border:1px solid #2f3a4d;background:#161b23}
.gA{color:#2ee6a8;border-color:#1d5c47;background:#0d241d}
.gB{color:#9ad8ff;border-color:#1d4a5c;background:#0d2029}
.gC{color:#ffd166;border-color:#5c4a1d;background:#241f0d}
.gD,.gF{color:#ff8080;border-color:#5c2020;background:#2a1010}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;color:#6f7787;font-weight:500;font-size:11px;letter-spacing:.1em;text-transform:uppercase;padding:0 0 10px}
td{padding:13px 10px;border-top:1px solid #191d26;vertical-align:top}
td:first-child{padding-left:0}
.name{font-weight:600}
.det{color:#7f8798;font-size:12.5px;margin-top:2px}
.pts{font-variant-numeric:tabular-nums;color:#98a0b0;white-space:nowrap}
.bar{height:5px;border-radius:3px;background:#1a1f28;overflow:hidden;width:110px}
.bar i{display:block;height:100%;background:#2ee6a8;border-radius:3px}
.bar.low i{background:#ff6b6b}.bar.mid i{background:#ffc14d}
.foot{margin-top:36px;padding-top:22px;border-top:1px solid #191d26;color:#6f7787;font-size:12.5px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
a{color:#8ab4ff;text-decoration:none}
</style></head><body><div class="wrap">
<div class="top"><span class="dot"></span> Gatecheck report</div>
<h1>@@REPO@@</h1>
<p class="sub">@@STARS@@ stars · @@FILES@@ files · @@SKILLS@@ skills · scanned @@WHEN@@</p>
<div class="hero">
  <div><div class="num">@@SCORE@@<small>/100</small></div></div>
  <div><span class="badge g@@GRADE@@">Grade @@GRADE@@</span>
  <div class="det" style="margin-top:10px;max-width:430px">@@VERDICT@@</div></div>
</div>
<table><tr><th>Signal</th><th>Points</th><th></th></tr>
@@ROWS@@
</table>
<div class="foot"><span>Gatecheck · deterministic, no LLM, ~10s per repo</span><span>@@FOOT@@</span></div>
</div></body></html>"""


def verdict(rep: Report) -> str:
    worst = sorted(rep.signals, key=lambda s: s.score)[:2]
    if rep.total >= 85:
        return "This repo is ready for agent work. " + worst[0].detail.capitalize() + "."
    return "Biggest gaps: " + " · ".join(f"{w.label} — {w.detail}" for w in worst) + "."


def render(rep: Report) -> str:
    rows = []
    for s in rep.signals:
        cls = "low" if s.score < 0.5 else "mid" if s.score < 0.85 else ""
        rows.append(
            f"<tr><td><div class='name'>{s.label}</div><div class='det'>{s.detail}</div></td>"
            f"<td class='pts'>{s.points}/{s.weight}</td>"
            f"<td><div class='bar {cls}'><i style='width:{max(4, s.score*100):.0f}%'></i></div></td></tr>")
    return (PAGE.replace("@@REPO@@", rep.repo).replace("@@SCORE@@", f"{rep.total:.0f}")
            .replace("@@GRADE@@", rep.grade).replace("@@STARS@@", f"{rep.stars:,}")
            .replace("@@FILES@@", str(rep.files_scanned)).replace("@@SKILLS@@", str(rep.skills))
            .replace("@@WHEN@@", datetime.now().strftime("%d %b %Y"))
            .replace("@@VERDICT@@", verdict(rep)).replace("@@ROWS@@", "\n".join(rows))
            .replace("@@FOOT@@", "free scan · gatecheck.dev"))


def to_markdown(rep: Report) -> str:
    lines = [f"### Gatecheck — `{rep.repo}`: **{rep.total:.0f}/100** (grade {rep.grade})", "",
             "| Signal | Points | Detail |", "|---|---|---|"]
    for s in rep.signals:
        lines.append(f"| {s.label} | {s.points}/{s.weight} | {s.detail} |")
    worst = sorted(rep.signals, key=lambda s: s.score)[:2]
    lines += ["", "**Fix first:** " + " · ".join(f"{w.label} — {w.detail}" for w in worst)]
    return "\n".join(lines)


def main() -> None:
    global LOCAL_ROOT
    args = sys.argv[1:]
    targets = [a for a in args if not a.startswith("--")]
    out = next((a.split("=", 1)[1] for a in args if a.startswith("--out=")), str(ROOT / "out"))
    csvf = next((a.split("=", 1)[1] for a in args if a.startswith("--csv=")), None)
    statsf = next((a.split("=", 1)[1] for a in args if a.startswith("--stats=")), None)
    lista = next((a.split("=", 1)[1] for a in args if a.startswith("--file=")), None)
    jsonout = next((a.split("=", 1)[1] for a in args if a.startswith("--json-out=")), None)
    localdir = next((a.split("=", 1)[1] for a in args if a.startswith("--local=")), None)
    markdown = "--markdown" in args
    workers = int(next((a.split("=", 1)[1] for a in args if a.startswith("--workers=")), "4"))

    if localdir is not None:
        LOCAL_ROOT = Path(localdir).resolve()
        targets = [LOCAL_ROOT.name or "."]
        print(f"local scan: {LOCAL_ROOT}")

    if lista:
        targets += [l.strip() for l in Path(lista).read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]
    Path(out).mkdir(parents=True, exist_ok=True)
    if not targets:
        print("no target repos"); return

    results: list[Report] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for rep in ex.map(audit, targets):
            results.append(rep)
            if jsonout:
                p = Path(jsonout)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({"repo": rep.repo, "score": rep.total, "grade": rep.grade,
                                         "signals": [dict(asdict(s), points=s.points) for s in rep.signals]},
                                        ensure_ascii=False, indent=2), encoding="utf-8")
            if markdown:
                print(to_markdown(rep))
            if rep.error:
                print(f"  ERR  {rep.repo}: {rep.error}")
                continue
            slug = rep.repo.replace("/", "__")
            (Path(out) / f"{slug}.json").write_text(json.dumps(
                {"repo": rep.repo, "score": rep.total, "grade": rep.grade,
                 "signals": [dict(asdict(s), points=s.points) for s in rep.signals]}, ensure_ascii=False, indent=2), encoding="utf-8")
            (Path(out) / f"{slug}.html").write_text(render(rep), encoding="utf-8")
            print(f"{rep.total:>5.1f} {rep.grade}  {rep.repo:<44} skills={rep.skills:<3} ctx={rep.ctx_chars:<6} "
                  f"truth={rep.truth_ok}/{rep.truth_ok + rep.truth_fail}")

    ok = [r for r in results if not r.error]
    if csvf and ok:
        rows = [r.row() for r in ok]
        keys = sorted({k for r in rows for k in r})
        with open(csvf, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(f"\nCSV -> {csvf} ({len(rows)} rows)")

    if ok:
        n = len(ok)
        agg = {
            "audited": n,
            "avg_score": round(sum(r.total for r in ok) / n, 1),
            "median_score": round(sorted(r.total for r in ok)[n // 2], 1),
            "grades": {g: sum(1 for r in ok if r.grade == g) for g in "ABCDF"},
            "no_context_file_pct": round(100 * sum(1 for r in ok if not r.ctx_chars) / n, 1),
            "stale_90d_pct": round(100 * sum(1 for r in ok if r.ctx_days is not None and r.ctx_days > 90) / n, 1),
            "over_budget_pct": round(100 * sum(1 for r in ok if r.ctx_chars > HARD) / n, 1),
            "has_skills_pct": round(100 * sum(1 for r in ok if r.skills) / n, 1),
            "broken_claims_repos_pct": round(100 * sum(1 for r in ok if r.truth_fail > 0) / n, 1),
            "truth_claims_total": sum(r.truth_ok + r.truth_fail for r in ok),
            "truth_ok_total": sum(r.truth_ok for r in ok),
            "signals": {s.key: round(100 * sum(next((x.score for x in r.signals if x.key == s.key), 0) for r in ok) / n, 1)
                        for s in ok[0].signals},
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if statsf:
            Path(statsf).write_text(json.dumps(agg, indent=2), encoding="utf-8")
        print("\n== aggregate ==")
        for k, v in agg.items():
            if k != "signals":
                print(f"  {k:<26} {v}")
        for k, v in agg["signals"].items():
            print(f"  sig:{k:<22} {v}%")


if __name__ == "__main__":
    main()
