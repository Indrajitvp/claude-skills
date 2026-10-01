---
name: flow-setup
description: One-time setup for /flow in a repo — probe how it builds, tests and commits, then record it to .flow/config.md.
disable-model-invocation: true
---

# Flow setup

Probe the repo, confirm each finding with the user, write `.flow/config.md`. Run
once per repo.

## Probe, then confirm

Work each of these out from the repo, present it as a default, let the user
correct:

1. **Verify command** — the one command that typechecks, lints and tests. Look in
   `package.json` scripts (`verify`, `check`, `ci`), `Makefile`, `justfile`,
   `CONTRIBUTING`. With no single command, propose a chain (e.g.
   `tsc --noEmit && eslint . && vitest run`).
2. **Single-test command** — how to run one test file, for the tdd loop.
3. **Commit target** — does the user land work straight on `main` here
   (`commit-to-main: true`) or branch + PR (`false`)? Default `false` unless it is
   plainly a solo repo.
4. **Tracker** — where plans live. Default `.flow/<slug>/`. Record something else
   only if the repo already tracks work there (GitHub Issues, Linear).
5. **Domain docs** — is there a `CONTEXT.md`? Where do ADRs live? Record the paths
   that exist; do not create them.

## Write the config

`.flow/config.md`:

```
# Flow config

verify: <command>
test-one: <command>
commit-to-main: <true|false>
tracker: .flow/<slug>/
context: CONTEXT.md            # line omitted if absent
adr: docs/adr/                 # line omitted if absent
```

Commit it: `[CHORE] Add flow config`.
