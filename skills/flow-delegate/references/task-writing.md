# Writing tasks a weaker model cannot get wrong

Every rule here comes from a failure that actually happened when Qwen3-Coder-480B ran
through Cline on a real repo. The model is capable at small, fully specified edits and
unreliable at deciding, remembering, and verifying. So: decide everything in the task,
keep each task small, and let a script judge.

## The shape of a task

```
# 03 parser: placements_parse.py
tag: FEATURE
check: --backend
allow: src/etl/placements_parse.py
allow: tests/test_placements_parse.py
verify: python src/etl/placements_parse.py
expect: Processed 1268 students
---
<body>
```

`allow:` is enforced by the driver. A change outside it fails the attempt, so list
every file the task may touch, and nothing else.

## Rules

1. **One deliverable per task.** One new file, or one function, or one component.
   If the body needs more than about 60 lines, split it. Failures grow with size
   (a 140-line `schema.py` rewrite looped fifteen times).
2. **Prefer a new file to an edit.** New files cannot be pasted into the wrong place.
   To wire a new file into an old one, give the exact anchor text and the exact lines
   to add ("after the line `app.include_router(meta.router)` add `app.include_router(placements.router)`").
   Never "update the list" or "add this near the bottom".
3. **Never ask for a rewrite of an existing file.** A from-memory rewrite of `schema.py`
   silently dropped a table and every index. Allowed shapes: append, insert after an
   exact anchor, replace an exact quoted block.
4. **Tests first, written by you.** For any logic, put the finished test file in the
   repo (or paste it in the task) and make the task "make these tests pass". The model
   then has an exact target and the judge is the test runner.
5. **Paste ground truth, never describe it.** Real column headers, three real data rows,
   the real JSON shape, real function signatures. A task that said "read the CSV" produced
   code using `Reg No` when the header is `Register Number`.
6. **Name the pattern file.** "Copy the structure of `webapp/backend/routers/students.py`."
   "Follow `components/student-table.tsx`." The model imitates well and designs badly.
7. **Make every decision in the task.** No "decide", "design", "choose", "figure out",
   "as appropriate". Column order, names, defaults, edge cases, status codes: all stated.
8. **State the prohibitions.** Do not create scratch or backup files. Do not delete and
   recreate a file. Do not touch files outside `allow:`. Do not run slow jobs
   (name them).
9. **Each task must leave the tree green and produce its own inputs.** Never depend on an
   artifact a previous task "should" have made unless that task's `verify:` proves it
   exists. (A loader task depended on a CSV that no task produced.)
10. **The verify command prints a number or phrase.** `expect:` text such as
    `Processed 1268 students` or `OK` cannot be argued with. "Works correctly" can.
11. **Frontend tasks verify only types and lint.** `tsc -b` + `oxlint`. Visual quality is the
    user's to judge: never ask the model to screenshot or drive a browser. State props,
    hook names, token classes, and the component to copy. Remind it that unused imports
    fail `tsc`.
12. **Keep the prompt short, put detail in the file.** The driver's prompt only points at
    the task file. Long inline prompts get truncated or quoted wrongly.
13. **Order for safety.** Tests, then pure functions, then I/O, then wiring, then UI.
    Put fragile shared files (schema, build scripts, `main.py`) in their own one-line
    wiring task with an exact anchor.

## Body template

```
Goal: <one or two sentences, user-visible effect first>.

Create/edit: <exact path(s)>.
Copy the structure of: <pattern file>.

Ground truth:
<pasted headers / rows / JSON / signatures>

Exact behaviour:
- <input> -> <output>   (3 or more real examples, including an empty/edge case)

Do not: <prohibitions>.
Done when: `<verify command>` prints `<expected text>` and `python automation/check.py <flag>` prints RESULT: PASS.
```

## Sizing guide

| Work | Task size |
|---|---|
| Pure function + tests | 1 task |
| New DB table | 1 task: append one SQL constant + one index line after named anchors |
| New API route | 1 task for the SQL builder + test, 1 task for the route + test |
| React component | 1 task per component; hooks and types in their own earlier task |
| Wiring into `App.tsx` / `main.py` | its own tiny task with exact anchors |

## When a task is STUCK

Read only `automation/runs/<slug>/<task>-feedback<N>.md`. Typical fixes, in order:
1. The spec was ambiguous: add the missing ground truth or example and rerun `--only NN`.
2. The task was too big: split it.
3. It is a 3-line fix: do it yourself and commit, then continue with the next task.
Do not rerun an unchanged task a fourth time.
