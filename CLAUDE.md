# Working habits

These apply in every repo, whether or not `/flow` is running.

- **Visual review is the user's.** Never drive a browser, Playwright or a headless
  renderer, and never take screenshots, to check UI work. Verify statically —
  build, typecheck, lint, read the file — and describe what changed in words. Ask
  the user when something genuinely needs a visual judgement.

- **Pair every technical summary with plain language.** Alongside the file and
  function detail, say what actually changes for a person using the product — what
  they would notice, what problem it solves. Keep the technical detail; add the
  plain-language layer on top of it.

- **Verify before handing back.** Run the repo's verify step (or at least
  typecheck, lint and tests) before calling work done, and report the real
  result. If it fails and you are not fixing it now, say so.

- **Ship verified work on your own initiative.** Once a change is clean, commit
  and push it without waiting to be asked. The `ship` skill has the message
  format and where it lands. Never force-push or `--no-verify` without an explicit
  ask.

- **Commit messages: bracket-tag, no trailers.** `[FEATURE] add X` style, at most
  two plain-prose body lines, no `Co-Authored-By` or any other trailer, no names
  or meeting references. Full rules in the `ship` skill.
