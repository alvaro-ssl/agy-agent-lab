---
name: parallel-team
description: >-
  Runs an engineering team of parallel subagents. Use when the user runs /parallel-team or asks to fix or build
  several components at once (for example backend and frontend) with subagents, then integrate and verify.
---

# Parallel engineering team (`/parallel-team`)

## 1. Agree the contract first

Before spawning anyone, write down the interfaces the subagents share — API routes, field names, types and
units, file ownership. Parallel work fails at the seams: if the backend and frontend subagents each "fix"
their side differently, the integration breaks.

## 2. Partition by ownership

Give each subagent a non-overlapping set of files and the shared contract, for example:

- **Backend engineer** — owns `app.py` and server-side data access.
- **Frontend engineer** — owns `static/` (HTML, CSS, JS).
- **Test engineer** (optional) — owns `tests/`; writes checks against the contract, not the implementation.

Spawn them in a single `invoke_subagent` call so they run concurrently.

## 3. Integrate and verify

1. Review each subagent's diff against the contract.
2. Run the full test suite and start the app.
3. Verify in a real browser (`/browser` skill) — screenshots, not assumptions.
4. Loop until every check passes; report what each subagent changed and the evidence that it works.
