---
name: executive-stress-test
description: >-
  Multi-perspective stress test of a system, release or plan. Spawns parallel read-only subagents that each
  take an executive lens (CTO: performance and resilience, CISO: security and trust, COO/CFO: operational and
  business risk) and synthesises one prioritised blueprint. Use when the user invokes /executive-stress-test
  or asks to stress-test something from several leadership perspectives before acting.
---

# Executive multi-perspective stress test (`/executive-stress-test`)

## 1. Fan out (one tool call, parallel, read-only)

Use `invoke_subagent` to launch three concurrent read-only subagents on the target the user named:

- **CTO — performance & resilience**: latency, scalability, failure modes, whether monitoring and health
  checks would actually detect a problem, and what the rollback path is.
- **CISO — security & trust**: secrets, input handling, access to production actions, what an agent or user
  could do that they should not.
- **COO/CFO — operations & business risk**: customer and revenue impact, on-call load, change-management and
  approval rules in `.agents/rules/`, and what leadership would need to sign off.

Each subagent returns evidence-backed findings (file and line, or a reproducible observation) with severity.

## 2. Synthesise

Merge the three reports into one **blueprint**:

1. **Risk matrix** — one row per finding: lens, severity, evidence, business impact.
2. **Decisions for leadership** — the trade-offs that need a human call, each with the options and their
   consequences (no recommended option unless the user asks for one).
3. **Remediation plan** — file-by-file or step-by-step, with the verification that proves each fix.
