#!/usr/bin/env python3
"""The one judge. Exit code 0 only if every step passes. ASCII output only.

    python automation/check.py            # everything
    python automation/check.py --backend  # skip frontend steps
    python automation/check.py --frontend # only frontend steps

Run from anywhere; it always works from CGPA_Analysis/.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # keep the git tree clean; children inherit this
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "webapp" / "frontend"
PY_DIRS = ["src/etl", "webapp/backend", "tests", "automation"]
SCRATCH = re.compile(r"(\.bak|\.orig|\.clean\d*|\.final|\.tmp)$|^test_syntax\.py$")

results: list[tuple[str, bool, float]] = []


def run(name: str, cmd: list[str], cwd: Path = ROOT, tail: int = 25) -> bool:
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok, out = p.returncode == 0, (p.stdout + p.stderr).strip()
    except FileNotFoundError as e:
        ok, out = False, f"command not found: {e}"
    results.append((name, ok, time.time() - t0))
    if not ok:
        print(f"\n--- FAIL: {name} ---")
        print("\n".join(out.splitlines()[-tail:]))
    return ok


def check_python_syntax() -> bool:
    """Compile in-process (py_compile would write __pycache__ and dirty the git tree)."""
    files = [f for d in PY_DIRS if (ROOT / d).is_dir() for f in (ROOT / d).rglob("*.py") if "__pycache__" not in f.parts]
    if not files:
        return skip("python syntax (no python dirs found)")
    t0, errors = time.time(), []
    for f in files:
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except (SyntaxError, ValueError) as e:
            errors.append(f"{f.relative_to(ROOT)}: {e}")
    results.append(("python syntax", not errors, time.time() - t0))
    if errors:
        print("\n--- FAIL: python syntax ---\n" + "\n".join(errors[:15]))
    return not errors


def check_no_scratch_files() -> bool:
    bad = [str(f.relative_to(ROOT)) for d in ("src", "webapp/backend", "tests", "automation", ".")
           for f in (ROOT / d).glob("*" if d == "." else "**/*")
           if f.is_file() and SCRATCH.search(f.name) and "node_modules" not in f.parts and "venv" not in f.parts]
    ok = not bad
    results.append(("no scratch files", ok, 0.0))
    if not ok:
        print("\n--- FAIL: no scratch files ---\nDelete these:", *sorted(set(bad)), sep="\n  ")
    return ok


def skip(name: str) -> bool:
    results.append((name + " [skipped]", True, 0.0))
    return True


def check_no_pii_columns() -> bool:
    schema = ROOT / "src" / "etl" / "schema.py"
    if not schema.exists():  # repo-specific guard; delete or adapt for other repos
        return skip("placement tables PII guard")
    text = schema.read_text(encoding="utf-8")
    block = re.findall(r"CREATE TABLE IF NOT EXISTS placement\w*\s*\((.*?)\n\s*\)", text, re.S)
    hit = [b for b in block if re.search(r"mobile|email", b, re.I)]
    results.append(("placement tables have no mobile/email", not hit, 0.0))
    if hit:
        print("\n--- FAIL: mobile/email column in a placement table (PII) ---")
    return not hit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", action="store_true", help="skip frontend steps")
    ap.add_argument("--frontend", action="store_true", help="only frontend steps")
    a = ap.parse_args()
    do_back, do_front = not a.frontend, not a.backend

    if do_back:
        check_python_syntax()
        check_no_scratch_files()
        check_no_pii_columns()
        if (ROOT / "tests").is_dir():
            run("unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        else:
            skip("unit tests (no tests/ dir)")
        if (ROOT / "webapp" / "backend" / "main.py").exists():  # repo-specific: adapt or delete
            run("backend imports", [sys.executable, "-c", "from webapp.backend.main import app"])
    if do_front:
        if (FRONTEND / "package.json").exists():
            npx = shutil.which("npx") or "npx"
            run("frontend tsc -b", [npx, "tsc", "-b"], cwd=FRONTEND)
            run("frontend oxlint (errors only)", [npx, "oxlint", "--quiet"], cwd=FRONTEND)
        else:
            skip("frontend (no webapp/frontend/package.json)")

    print("\n=== CHECK SUMMARY ===")
    for name, ok, secs in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} ({secs:.1f}s)")
    failed = [n for n, ok, _ in results if not ok]
    print("RESULT: PASS" if not failed else f"RESULT: FAIL ({len(failed)} failing)")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
