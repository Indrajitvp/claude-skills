---
name: flow-delegate
description: Hand a /flow phase's build step to the Cline CLI (a cheaper model) and run it unattended, judged by a script. Use when the user picks "Executor: Cline" in /flow, or says delegate, run it with Cline, or run the tasks headless.
disable-model-invocation: true
---

# Flow delegate

The build step of a `/flow` phase, done by Cline instead of Claude. Claude writes
small tasks and reviews; Cline writes the code; **`automation/check.py` decides
pass or fail, never the model's own summary.** The user can be away while it runs.

Everything else in `/flow` is unchanged: inventory, grill, plan, review, ship.

## When to use it

Delegate work that is large, mechanical, and checkable by one command: new files,
components, routes, tests, boilerplate. Do it yourself when it is small, fiddly, or
already failed twice: edits to fragile shared files, repairing broken code, anything
that needs a decision. Say which you chose and why in one line.

## Preconditions (check, do not assume)

1. `cline --version` works. If not: `npm install -g cline`.
2. Cline has a provider. Check `~/.cline` exists / ask the user whether they ran
   `cline auth -p openai -b <base-url> -m <model-id> -k <key>`. **Never ask the user
   to paste a key into the chat.** If it is not done, give them the command and stop.
3. The repo has `automation/check.py`, `automation/run_tasks.py`, `ARCHITECTURE.md`.
   If not, run **Bootstrap** below.
4. Git tree is clean (`git status --porcelain` empty). Commit or stash first, on a
   non-default branch. The driver resets failed attempts with `git reset --hard`.
5. `python automation/selftest/run_selftest.py` prints `SELFTEST PASS` (once per repo,
   and after any change to the driver).

## Steps

1. **Pick the phase.** From `.flow/<slug>/plan.md`, the first phase whose `Status:` is
   not `shipped`. Announce it as `/flow` does.
2. **Split into tasks.** Read `references/task-writing.md` first, every time. Write
   `tasks/<slug>/NN-name.md`, one small task each. Write the tests yourself where there
   is logic. Run `python automation/run_tasks.py <slug> --dry-run` and show the user the
   list (title, check flag, allowed files). Commit the task files alone
   (`[DOCS] add <slug> tasks`).
3. **Launch.** `python automation/run_tasks.py <slug>` with the Bash tool and
   `run_in_background: true`. Do not poll. You will be notified when it exits.
   Tell the user they can leave; the run writes `automation/runs/<slug>/report.md`.
4. **Read only the report.** `automation/runs/<slug>/report.md` (it names the base
   branch, per-task attempts, tokens and cost) and `git diff <base>..auto/<slug> --stat`.
   Do not read agent logs (`*.jsonl`) unless a task is stuck and the feedback file is
   not enough. This is where the token saving comes from. Exit codes: 0 all done,
   2 a task is stuck, 3 halted on an authentication error (tell the user to run
   `cline auth`; nothing was committed).
5. **Resume.** Rerunning `run_tasks.py <slug>` skips tasks already committed on the
   branch, so a stopped run continues where it stopped. `--redo` forces them again.
   **If a task is STUCK,** Read its `*-feedback<N>.md`. Fix per the "STUCK" section of
   `references/task-writing.md`: sharpen the spec and `--only NN`, split it, or fix it
   yourself. Do not rerun an unchanged task.

   **Fallback to Claude.** Stop delegating a phase and build it yourself (Executor:
   claude) when any of these is true:
   1. the same task is stuck twice after you sharpened its spec;
   2. more than a third of the phase's tasks needed a second attempt (the report's
      attempts column);
   3. the stuck task edits a fragile shared file (schema, build script, main entry point).

   Tell the user in one line which rule triggered, set `Executor: claude` on that phase
   in the plan, and continue from the last passing commit on `auto/<slug>`. These
   thresholds are guesses; tune them from measured runs.
6. **Review.** Invoke `mattpocock-skills:code-review` against the phase's start commit
   with `.flow/<slug>/plan.md` as the spec. Apply must-fix findings yourself (small) or
   as a new task. Re-run `python automation/check.py` (the repo's `verify`).
7. **Ship.** Invoke `ship`. The work sits on `auto/<slug>`; follow `commit-to-main` in
   `.flow/config.md` (branch + PR when false). Set the phase `Status: shipped`.
8. **Close.** Plain-language summary of what changed for a person using the product,
   plus the technical detail, and the next phase.

## Rules for the run

- The driver never pushes and never touches ignored files (`data/`). Keep it that way.
- Cline runs with approvals off. Never point it at a repo with uncommitted work, a
  shared branch, or secrets in the tree.
- Visual review stays the user's. Frontend tasks verify with `tsc` and lint only.
- A task that fails three times stops the whole run. That is by design: report it,
  do not loop.
- Never edit `Status:` lines from inside a task. Only this skill, after review.

## Bootstrap a repo (once)

1. `python ~/.claude/skills/flow-delegate/scripts/install.py <repo>` copies the driver,
   `check.py`, self-test, `config.json` and a generic `.clinerules` into the repo and
   adds `__pycache__/`, `*.pyc`, `automation/runs/` to `.gitignore`. It never overwrites
   (use `--force`). `--diff <repo>` shows drift from the templates; `--pull <repo>`
   copies improved repo versions back into the templates (not `check.py`,
   `config.json` or `.clinerules`, which are per repo).
2. **Adapt `check.py`**: set `PY_DIRS`; add the repo's own test and typecheck commands;
   delete the CGPA-specific guards. Steps whose inputs are missing are skipped. Keep
   the contract: exit 0 only when everything passes, ASCII output only, nothing that
   writes into the git tree (no `py_compile`, no `__pycache__`).
3. Write `<repo>/ARCHITECTURE.md` for agents: folder map, data flow, conventions,
   commands, known pitfalls. Explore the repo for real facts; do not guess.
4. Edit `.clinerules` with the repo's own hard rules (what never to touch, slow jobs
   not to run, PII). Set `provider` and `model` in `automation/config.json`.
5. Commit, then `python automation/selftest/run_selftest.py` must print `SELFTEST PASS`.
6. Tell the user to run `cline auth` themselves.

## Known limits

- Cline and the model it drives can still write wrong code that passes weak checks.
  The check is only as good as the tests: write real ones.
- Verified against Cline CLI 3.0.68: headless runs work without a terminal, `--json`
  prints JSON lines, `-P openai` maps to the OpenAI-compatible provider, and a missing
  key gives `errorClass: auth` with exit 1. Not yet verified with a live key: file edits,
  whether the CLI picks up `.clinerules`, and real token counts. If a flag changes,
  update `run_agent()` and `parse_log()` in `run_tasks.py` and rerun the self-test.
- Estimated unattended time is up to about an hour per phase. Treat that as a guess
  until measured on a real run.
- The driver assumes one run at a time per repo and a clean working tree.
