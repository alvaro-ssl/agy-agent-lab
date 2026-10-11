---
name: review
description: >-
  Staff-engineer code review of a commit, diff (e.g. HEAD~1..HEAD), branch or set of files. Use when the user
  runs /review or asks for a thorough review to catch correctness, performance, reliability, security and
  governance problems before or after a release.
---

# Staff-engineer code review (`/review`)

Produce a rigorous, high-signal, read-only review of the requested change and return a structured report.

## 1. Boundaries

- **Read-only**: audit and report. Do not modify files or git history unless the user asks for fixes in the
  same turn.
- **Verify before reporting**: read the surrounding code and callers, and run the code or tests when that is
  the quickest way to confirm a suspicion. Report only what you have evidence for.

## 2. Method

1. **Resolve scope.** For a commit range, run `git show --stat` and `git diff <range>` inside the project
   (e.g. `cymbal-control-tower/`). With no range, review uncommitted changes, else `HEAD~1..HEAD`.
2. **Read whole files**, not just hunks — regressions often come from a change in one file that another file
   still depends on.
3. **Check each risk dimension:**
   - **Correctness & contracts** — do producers and consumers still agree on field names, types and units?
     Are aggregations mathematically right for what they claim to show?
   - **Performance** — blocking calls or per-item queries inside request handlers; work that scales with data
     size on every request.
   - **Reliability & observability** — do health checks and status indicators measure reality, or can they
     report green while users suffer?
   - **Security** — secrets, injection, unsafe handling of user input.
   - **Governance** — does the change respect the rules in `.agents/rules/`?
4. **Check the tests.** Would the existing tests have caught each finding? If not, say what test would.

## 3. Output

1. **Verdict** — `REQUEST CHANGES`, `APPROVE WITH SUGGESTIONS` or `APPROVE`, plus a 2–3 sentence summary.
2. **Findings**, most severe first (`P1` blocking → `P3` low). For each: severity and category, file and line
   links, what breaks and for whom (a concrete failure scenario), and the recommended fix.
3. **Test gaps** — the tests that would have caught the P1/P2 findings.
