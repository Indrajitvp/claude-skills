"""Proves the driver logic without a model: python automation/selftest/run_selftest.py
No model, no network, no key needed. Leaves the repo as it found it."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAKE = f'"{sys.executable}" automation/selftest/fake_agent.py'


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def drive(env_extra, *args):
    env = {**os.environ, "CLINE_BIN": FAKE, **env_extra}
    return subprocess.run([sys.executable, "automation/run_tasks.py", "_selftest", "--attempts", "2", *args],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def scenario(name, steps, want_commits):
    """steps: list of (env, args, want_exit, must_contain_in_stdout)."""
    start = git("branch", "--show-current")
    shutil.rmtree(ROOT / "automation" / "runs" / "_selftest", ignore_errors=True)
    ok, notes = True, []
    for env, args, want_exit, contains in steps:
        p = drive(env, *args)
        if p.returncode != want_exit:
            ok = False; notes.append(f"exit {p.returncode} != {want_exit}\n{p.stdout[-900:]}{p.stderr[-500:]}")
        if contains and contains not in p.stdout:
            ok = False; notes.append(f"missing {contains!r} in output")
    commits = len(git("log", "--oneline", f"{start}..auto/_selftest").splitlines())
    clean = git("status", "--porcelain") == ""
    if commits != want_commits or not clean:
        ok = False; notes.append(f"commits={commits} (want {want_commits}) clean={clean}")
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    for n in notes:
        print("   ", n)
    git("checkout", start)
    git("branch", "-D", "auto/_selftest")
    return ok


G = {"FAKE_MODE": "good"}
results = [
    scenario("good task commits", [(G, ["--only", "01"], 0, "judge=PASS")], 1),
    scenario("bad task is reverted, run stops", [({"FAKE_MODE": "bad"}, ["--only", "01"], 2, "judge=FAIL")], 0),
    scenario("stray scratch file rejected", [({"FAKE_MODE": "scratch"}, ["--only", "01"], 2, "judge=FAIL")], 0),
    scenario("retry sees failure and fixes", [({"FAKE_MODE": "fix_on_retry"}, ["--only", "01"], 0, "attempt 2/2")], 1),
    scenario("auth error halts at once", [({"FAKE_MODE": "auth"}, ["--only", "01"], 3, "authentication error")], 0),
    scenario("token usage in report", [(G, ["--only", "01"], 0, "tokens=100/20")], 1),
    scenario("stop at task 2, then resume skips task 1",
             [({**G, "FAKE_FAIL_TASK": "02"}, [], 2, "judge=FAIL"), (G, [], 0, "already done, skipping")], 2),
]
print("SELFTEST", "PASS" if all(results) else "FAIL")
sys.exit(0 if all(results) else 1)
