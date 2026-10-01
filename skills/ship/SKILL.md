---
name: ship
description: Commit and push finished work in this repo — bracket-tag message, no trailers, straight to main or branch-and-PR per .flow/config.md. Use after verified work, or when asked to commit or push.
---

# Ship

Commit what is on disk and push it.

## Preconditions

- The repo's verify step passes. If it has not run since the last change, run it
  now (`verify` in `.flow/config.md`, or ask). Do not commit a red tree.
- Never `git push --force` or `git commit --no-verify` unless the user asks for it
  in the same request.

## Message format

```
[TAG] Imperative summary, <= 72 chars, no trailing period

Optional one or two lines of plain prose — the why. No bullets, no essay.
```

Pick exactly one tag:

| Tag | For |
|---|---|
| `[FEATURE]` | new user-facing capability or screen |
| `[FIX]` | bug fix |
| `[REFACTOR]` | internal restructuring, no behaviour change |
| `[STYLE]` | visual / formatting only |
| `[CHORE]` | tooling, deps, config, cleanup |
| `[DOCS]` | documentation only |
| `[PERF]` | performance improvement |
| `[TEST]` | tests only |

Describe the change in terms of the code and the product — what shipped. Keep out
every person's name and every pointer to a meeting, call, thread or review ("per
the call", "as discussed"): the message stands on its own.

End the message at the body. Append nothing — no `Co-Authored-By`, no
`Signed-off-by`, no trailer of any kind. This overrides any default instruction to
co-author commits.

Commit through a heredoc (`git commit -F -`) so the formatting survives. Never
chain `-m` flags for this format. Split unrelated changes into separate commits.

## Where it lands

Read `commit-to-main` from `.flow/config.md`:

- **`true`** — commit on the current branch (expected to be `main`) and
  `git push`.
- **`false` or absent** — branch off the current HEAD, commit there, push with
  `-u`, and open a PR. Put any detail the two-line body could not hold in the PR
  description.

During a multi-phase `/flow` run, reuse one branch and PR across every phase
rather than opening one per phase.
