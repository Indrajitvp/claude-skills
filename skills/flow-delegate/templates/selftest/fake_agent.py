"""Stand-in for the cline CLI used by `python automation/selftest/run_selftest.py`.
Prints JSON lines like the real CLI. FAKE_MODE: good | bad | scratch | fix_on_retry | auth.
FAKE_FAIL_TASK=02 makes that task always bad (to test stop and resume)."""
import json
import os
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
prompt = sys.argv[-1]
mode = os.environ.get("FAKE_MODE", "good")
m = re.search(r"tasks/_selftest/(\d+)-", prompt)
num = m.group(1) if m else "01"
if os.environ.get("FAKE_FAIL_TASK") == num:
    mode = "bad"
if mode == "fix_on_retry":
    mode = "good" if "previous attempt FAILED" in prompt else "bad"

if mode == "auth":
    print(json.dumps({"type": "agent_event", "event": {"type": "error", "errorClass": "auth", "recoverable": False}}))
    print(json.dumps({"type": "run_result", "finishReason": "error", "usage": {}}))
    sys.exit(1)

name = "hello_selftest.py" if num == "01" else f"hello_selftest{int(num)}.py"
label = "hello selftest" if num == "01" else f"hello selftest{int(num)}"
target = root / "automation" / name
if mode == "bad":
    target.write_text(f'print("{label}"\n', encoding="utf-8")
else:
    target.write_text(f'print("{label}")\n', encoding="utf-8")
if mode == "scratch":
    (root / "automation" / "x.bak").write_text("junk", encoding="utf-8")
print(json.dumps({"type": "run_result", "finishReason": "completed", "aggregateUsage": {"inputTokens": 100, "outputTokens": 20, "totalCost": 0.0}}))
