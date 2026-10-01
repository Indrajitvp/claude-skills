---
name: flow
description: Orchestrate a piece of work phase by phase — inventory every ask in the source, break it down, grill the open decisions, write a plan, then implement each phase with verify, review and commit.
disable-model-invocation: true
---

# Flow

Turn whatever is already in the conversation — a transcript, notes, a rough idea —
into shipped work, one phase at a time. `/flow` does not fetch the input; it works
from what is in context.

Read `.flow/config.md` in the repo first. If it is missing, tell the user to run
`/flow-setup` and stop.

## Resume an existing plan

Look for `.flow/<slug>/plan.md` for this work. If one exists with any phase whose
`Status:` is not `shipped`, announce which phase you are resuming and go straight
to **Run each phase** at that phase. Skip steps 1–4.

## 1. Inventory the source

Number every ask in the source, in the order raised, before shaping any of it
into work. A transcript hides them: asks arrive mid-sentence, come back later in
different words, and sit between scheduling, praise and pleasantries that carry
none. Quote the source's own words wherever the wording is what decides scope —
"sorted everywhere, not only in contacts" binds more than a tidied paraphrase of
it does.

Give every item one disposition:

- **phase** — this plan will do it
- **done** — already true; prove it against the code and cite the file
- **deferred** — real, deliberately outside this plan
- **blocked** — waiting on someone else
- **non-code** — the user's to do, not the repo's

Post the numbered list with its dispositions. Complete when every item carries
one: a dropped ask is then something the user decided, not something they never
saw.

An ask that contradicts a decision already live in the repo is its own item —
surface the conflict and let the grill settle it.

Save the source itself into `.flow/<slug>/` alongside the plan. A transcript
that stays in one session's context is gone by the next one.

## 2. Break into phases

Draft the work as an ordered list of phases. A phase is the smallest slice that
ships something coherent and can be reviewed on its own — a vertical slice, not a
layer. Aim for 2–6. If it needs more than one session can hold, tell the user to
run `/mattpocock-skills:wayfinder` instead of continuing here.

Every **phase** item from the inventory lands in exactly one phase.

For each phase, write one plain-language line (what a person using the product
would notice) and one technical line.

## 3. Grill the open decisions

Invoke `mattpocock-skills:grilling`. Put every unresolved decision to the user —
data shape, edge cases, naming, scope boundaries — before any code. If the repo
has a `CONTEXT.md`, also invoke `mattpocock-skills:domain-modeling` so terms match
the project's language.

Continue only once the grill's frontier is empty and the user confirms.

## 4. Write the plan

Write `.flow/<slug>/plan.md` (`<slug>` = short kebab-case name for the work):

```
# <Title>

<One paragraph, plain language: what this delivers and why it matters.>

## Source items

<the numbered inventory, each line carrying its disposition>

## Decisions

- <question> → <resolved answer>

## Phase 1 — <name>
Status: pending
Scope: <plain language>. <technical>.
Done when: <observable condition>

## Phase 2 — <name>
Status: pending
Scope: ...
Done when: ...
```

Commit the plan on its own (`[DOCS] Add <slug> plan`) before Phase 1.

## Run each phase

For each phase in order:

1. **Announce** — post the phase's plain-language scope and technical scope.
   Wait for the user's go or a redirect.
2. **Build** — implement the slice. At the seams agreed in the grill, invoke
   `mattpocock-skills:tdd`. Do not test rendering.
3. **Verify** — run the `verify` command from `.flow/config.md`. Red tree: fix it
   when this phase is the cause; stop and report when it is pre-existing or
   unrelated. A hard bug → invoke `mattpocock-skills:diagnosing-bugs`. Never carry
   a red tree into review.
4. **Review** — invoke `mattpocock-skills:code-review` against the phase's start
   commit, passing `.flow/<slug>/plan.md` as the spec. Apply must-fix findings,
   then re-verify and re-review the fixes.
5. **Ship** — invoke `ship`. Set the phase's `Status: shipped` in `plan.md`.
6. **Close** — post the completion summary (plain language **and** technical) and
   the next phase's scope in the same message. The user moves it forward in one
   reply.

After the last phase, post a plain-language summary of everything that shipped.

## Work that arrives mid-flight

A fix raised outside the phases — "just do item 8", a bug found while building,
a follow-up the user asks for in passing — still belongs to the plan. Add it to
the inventory and give it a phase before shipping it; when it has already
shipped, record it as a shipped phase straight away. The plan stays the one
place that says what the source asked for and what answered it.
