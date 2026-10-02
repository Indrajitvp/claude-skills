#!/usr/bin/env python3
"""Install, diff or pull the flow-delegate automation files.

  python install.py <repo>            copy templates into <repo> (never overwrites; --force to overwrite)
  python install.py --diff <repo>     show which installed files differ from the templates
  python install.py --pull <repo>     copy the repo's versions back into the templates (keeps one source of truth)
"""
import argparse
import filecmp
import shutil
import sys
from pathlib import Path

T = Path(__file__).resolve().parent.parent / "templates"
# template path -> path inside the repo
MAP = {
    "check.py": "automation/check.py",
    "run_tasks.py": "automation/run_tasks.py",
    "config.json": "automation/config.json",
    "selftest/fake_agent.py": "automation/selftest/fake_agent.py",
    "selftest/run_selftest.py": "automation/selftest/run_selftest.py",
    "selftest/01-hello.md": "tasks/_selftest/01-hello.md",
    "selftest/02-hello2.md": "tasks/_selftest/02-hello2.md",
    "clinerules.template": ".clinerules",
}
NEVER_PULL = {"config.json", "clinerules.template", "check.py"}  # repo-specific; edited per repo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--pull", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    if not (repo / ".git").exists():
        sys.exit(f"{repo} is not a git repo (the driver needs git)")

    if a.diff:
        for t, r in MAP.items():
            dst = repo / r
            state = "missing" if not dst.exists() else ("same" if filecmp.cmp(T / t, dst, shallow=False) else "DIFFERS")
            print(f"{state:8} {r}")
        return
    if a.pull:
        for t, r in MAP.items():
            if t in NEVER_PULL or not (repo / r).exists():
                continue
            shutil.copyfile(repo / r, T / t)
            print(f"pulled {r}")
        return

    for t, r in MAP.items():
        dst = repo / r
        if dst.exists() and not a.force:
            print(f"kept    {r} (exists)")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(T / t, dst)
        print(f"wrote   {r}")
    gi = repo / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if "automation/runs/" not in text:
        gi.write_text(text.rstrip("\n") + "\n\n# flow-delegate run logs\nautomation/runs/\n", encoding="utf-8")
        print("updated .gitignore")
    print("\nNext: 1) adapt automation/check.py to this repo (PY_DIRS, test and typecheck commands)\n"
          "      2) write ARCHITECTURE.md  3) set provider/model in automation/config.json\n"
          "      4) commit, then: python automation/selftest/run_selftest.py   5) cline auth (you)")


main()
