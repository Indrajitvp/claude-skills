# claude-skills

Personal Claude Code setup: the `flow`, `flow-setup`, `flow-delegate` and `ship` skills plus global `CLAUDE.md`.

Install: run `./install.ps1` (Windows) or `./install.sh` (macOS/Linux), then restart Claude Code.

Each repo that uses flow also needs its own `.flow/config.md` (`verify` command, `commit-to-main`).

## flow-delegate (optional: build phases with the Cline CLI)

`/flow` can hand the build step of a phase to the Cline CLI, running unattended, while a script (`automation/check.py`) decides pass or fail. Claude writes small task files and reviews.

- One-time per machine: `npm install -g cline`, then run `cline auth` yourself with your provider, base URL, model and key (never paste the key into a chat).
- One-time per repo: `python ~/.claude/skills/flow-delegate/scripts/install.py <repo>`, then adapt `automation/check.py`, write `ARCHITECTURE.md`, and run `python automation/selftest/run_selftest.py` (expect `SELFTEST PASS`).
- Set `executor: cline` in the repo's `.flow/config.md` (or answer at the end of the `/flow` grill). Default is `claude`.
- If a delegated phase keeps failing, `flow-delegate` hands it back to Claude (rules are in its `SKILL.md`).
