#!/usr/bin/env python3
"""Run task files through the Cline CLI unattended. The script judges, not the model.

    python automation/run_tasks.py <slug>              # all tasks in tasks/<slug>/
    python automation/run_tasks.py <slug> --only 02    # one task
    python automation/run_tasks.py <slug> --dry-run    # print what would run
    (rerun after a stop: finished tasks are skipped; --redo forces them again)

Per task: snapshot commit -> cline (headless) -> scope guard -> check.py -> verify cmds
  PASS -> commit "[TAG] title" on branch auto/<slug>
  FAIL -> git reset --hard snapshot, retry with the failure text (max --attempts)
  stuck -> stop, write report, exit 2. Never pushes. Never touches ignored files (data/).

Task file format (tasks/<slug>/NN-name.md):
    # NN title
    tag: FEATURE            commit tag
    check: --backend        flag for check.py: --backend | --frontend | (empty = all)
    allow: src/etl/*.py     glob of files the task may change (repeatable, relative to CGPA_Analysis/)
    verify: python src/etl/placements_parse.py     extra command that must exit 0 (repeatable)
    expect: Processed 1268 students                text that verify output must contain (repeatable)
    ---
    <body: goal, exact names, examples>
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # keep the git tree clean
ROOT = Path(__file__).resolve().parent.parent
AUTO = ROOT / "automation"
CONFIG = AUTO / "config.json"
DEFAULTS = {"provider": "openai", "model": "", "timeout": 1500, "retries": 6, "attempts": 3}


def sh(cmd, check=False, **kw):
    kw.setdefault("cwd", ROOT)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if check and p.returncode != 0:
        raise SystemExit(f"command failed: {cmd}\n{p.stdout}{p.stderr}")
    return p


def git(*args, check=True):
    return sh(["git", *args], check=check)


def parse_task(path: Path) -> dict:
    head, _, body = path.read_text(encoding="utf-8").partition("\n---\n")
    t = {"file": path, "title": path.stem, "tag": "FEATURE", "check": "", "allow": [], "verify": [], "expect": [], "body": body.strip()}
    for line in head.splitlines():
        if line.startswith("# "):
            t["title"] = line[2:].strip()
        elif ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            k, v = k.strip().lower(), v.strip()
            if k in ("allow", "verify", "expect"):
                t[k].append(v)
            elif k in ("tag", "check"):
                t[k] = v
    return t


def changed_files() -> list[str]:
    out = git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
    files = [l[3:].strip().strip('"').replace("\\", "/") for l in out if l.strip()]
    return [f for f in files if "__pycache__" not in f and not f.endswith(".pyc")]


def out_of_scope(files: list[str], allow: list[str]) -> list[str]:
    if not allow:
        return []
    return [f for f in files if not any(fnmatch.fnmatch(f, g) for g in allow)]


def parse_log(log: Path) -> dict:
    """Read the agent's JSON-lines log: auth failure flag, finish reason, token usage, cost."""
    info = {"auth_error": False, "finish": "", "tokens_in": 0, "tokens_out": 0, "cost": 0.0}
    try:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"errorClass":"auth"' in line.replace(" ", ""):
                info["auth_error"] = True
            if line.startswith("{") and '"type":"run_result"' in line.replace(" ", ""):
                r = json.loads(line)
                u = r.get("aggregateUsage") or r.get("usage") or {}
                info.update(finish=r.get("finishReason", ""), tokens_in=u.get("inputTokens", 0),
                            tokens_out=u.get("outputTokens", 0), cost=u.get("totalCost", 0.0))
    except (OSError, ValueError):
        pass
    return info


def default_branch() -> str:
    """Branch the work will be merged into: origin/HEAD if set, else main, else master."""
    p = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip().split("/", 1)[-1]
    for name in ("main", "master"):
        if git("rev-parse", "--verify", name, check=False).returncode == 0:
            return name
    return git("branch", "--show-current").stdout.strip()


def already_done(branch: str, task_file: str) -> bool:
    """A task counts as done if a commit on the branch records it (resume support)."""
    p = git("log", branch, "--fixed-strings", f"--grep=Automated task {task_file};", "--format=%h", check=False)
    return bool(p.stdout.strip())


def run_agent(cfg: dict, task: dict, attempt: int, feedback: Path | None, logdir: Path) -> tuple[int, Path]:
    # CLINE_BIN lets the self-test swap in a fake agent: CLINE_BIN="python automation/selftest/fake_agent.py"
    base = shlex.split(os.environ["CLINE_BIN"]) if os.environ.get("CLINE_BIN") else [shutil.which("cline") or ""]
    if not base[0]:
        raise SystemExit("cline CLI not found. Install: npm install -g cline, then run: cline auth")
    rel = task["file"].relative_to(ROOT).as_posix()
    prompt = (f"Read ARCHITECTURE.md and .clinerules, then read the task file {rel} and do exactly that task. "
              f"Run `python automation/check.py {task['check']}` and make it print RESULT: PASS before you finish. "
              f"Touch only the files the task allows. Do not create scratch files.")
    if feedback:
        prompt += (f" This is attempt {attempt}. The previous attempt FAILED and was reverted. "
                   f"Read {feedback.relative_to(ROOT).as_posix()} for the exact failure and fix that cause.")
    cmd = [*base, "-c", str(ROOT), "--json", "--retries", str(cfg["retries"]), "-t", str(cfg["timeout"]), "-P", cfg["provider"]]
    if cfg["model"]:
        cmd += ["-m", cfg["model"]]
    cmd.append(prompt)
    log = logdir / f"{task['file'].stem}-attempt{attempt}.jsonl"
    with open(log, "w", encoding="utf-8") as f:
        try:
            p = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=cfg["timeout"] + 120)
            return p.returncode, log
        except subprocess.TimeoutExpired:
            return 124, log


def judge(task: dict) -> tuple[bool, str]:
    files = changed_files()
    if not files:
        return False, "No files changed. The task must produce a change."
    bad = out_of_scope(files, task["allow"])
    if bad:
        return False, "Files changed outside the allowed list:\n  " + "\n  ".join(bad) + f"\nAllowed: {task['allow']}"
    chk = sh([sys.executable, "automation/check.py", *task["check"].split()])
    if chk.returncode != 0:
        return False, "check.py failed:\n" + (chk.stdout + chk.stderr)[-3500:]
    seen = ""
    for v in task["verify"]:
        p = sh(v, shell=True)
        text = p.stdout + p.stderr
        if p.returncode != 0:
            return False, f"verify command failed: {v}\n{text[-2500:]}"
        seen += text
    for e in task["expect"]:
        if e not in seen:
            return False, f"verify output missing expected text: {e!r}\nGot:\n{seen[-1500:]}"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--only", help="task number prefix, e.g. 02")
    ap.add_argument("--attempts", type=int)
    ap.add_argument("--redo", action="store_true", help="rerun tasks already committed on the branch")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = {**DEFAULTS, **(json.loads(CONFIG.read_text()) if CONFIG.exists() else {})}
    if a.attempts:
        cfg["attempts"] = a.attempts
    tasks = [parse_task(p) for p in sorted((ROOT / "tasks" / a.slug).glob("*.md"))]
    if a.only:
        tasks = [t for t in tasks if t["file"].name.startswith(a.only)]
    if not tasks:
        raise SystemExit(f"no tasks found for slug {a.slug!r}")
    if a.dry_run:
        for t in tasks:
            print(f"{t['file'].name}: [{t['tag']}] {t['title']} | check={t['check'] or 'all'} | allow={t['allow']}")
        return 0

    branch = f"auto/{a.slug}"
    if git("status", "--porcelain").stdout.strip():
        raise SystemExit("Working tree is not clean. Commit or stash first so a failed attempt can be reverted safely.")
    runs = AUTO / "runs" / a.slug
    runs.mkdir(parents=True, exist_ok=True)
    base_file = runs / "base.txt"
    exists = git("rev-parse", "--verify", branch, check=False).returncode == 0
    if exists:
        git("checkout", branch)
        base = base_file.read_text().strip() if base_file.exists() else default_branch()
    else:
        base = git("branch", "--show-current").stdout.strip() or default_branch()
        git("checkout", "-b", branch)
        base_file.write_text(base, encoding="utf-8")

    rows, stuck, halted = [], None, None
    for t in tasks:
        name = t["file"].name
        if not a.redo and already_done(branch, name):
            print(f"\n== {name}: already done, skipping ==", flush=True)
            rows.append((name, t["title"], "SKIPPED (done)", 0, "", 0, 0, 0.0))
            continue
        feedback, ok, why, n = None, False, "", 0
        t_in = t_out = 0
        cost = 0.0
        for n in range(1, cfg["attempts"] + 1):
            sha = git("rev-parse", "HEAD").stdout.strip()
            print(f"\n== {name} attempt {n}/{cfg['attempts']} ==", flush=True)
            t0 = time.time()
            rc, log = run_agent(cfg, t, n, feedback, runs)
            info = parse_log(log)
            t_in += info["tokens_in"]; t_out += info["tokens_out"]; cost += info["cost"]
            if info["auth_error"]:
                halted = (f"Cline reported an authentication error (see {log.name}). Run `cline auth` "
                          f"with your provider, base URL, model and key, then rerun. Nothing was committed.")
                git("reset", "--hard", sha)
                git("clean", "-fd", check=False)
                break
            ok, why = judge(t)
            print(f"   agent exit={rc} judge={'PASS' if ok else 'FAIL'} tokens={info['tokens_in']}/{info['tokens_out']} ({time.time()-t0:.0f}s)", flush=True)
            if ok:
                git("add", "-A")
                git("commit", "-q", "-m", f"[{t['tag']}] {t['title']}", "-m", f"Automated task {name}; check.py passed.")
                break
            feedback = runs / f"{t['file'].stem}-feedback{n}.md"
            feedback.write_text(f"# Failure of attempt {n} for {name}\n\n{why}\n\n(agent exit code {rc})\n", encoding="utf-8")
            git("reset", "--hard", sha)
            git("clean", "-fd", check=False)
        if halted:
            break
        rows.append((name, t["title"], "PASS" if ok else "FAIL", n, "" if ok else why, t_in, t_out, cost))
        if not ok:
            stuck = t
            break

    lines = [f"# Run report: {a.slug}", f"\nBranch `{branch}` (base `{base}`), {datetime.now():%Y-%m-%d %H:%M}\n",
             "| task | title | result | attempts | tokens in/out | cost |", "|---|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[5]}/{r[6]} | {r[7]:.4f} |" for r in rows]
    if halted:
        lines += ["", "## HALTED", halted]
    if stuck:
        lines += ["", f"## STUCK at {stuck['file'].name}", "```", rows[-1][4][-3000:], "```",
                  "Tree was reset to the last passing commit. Logs: automation/runs/" + a.slug]
    lines += ["", "## Commits on branch", "```", git("log", "--oneline", f"{base}..HEAD", check=False).stdout.strip(), "```"]
    (runs / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport: {runs / 'report.md'}")
    if halted:
        print(halted)
        return 3
    return 2 if stuck else 0


if __name__ == "__main__":
    raise SystemExit(main())
