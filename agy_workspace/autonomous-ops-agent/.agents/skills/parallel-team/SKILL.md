---
name: parallel-team
description: >-
  Autonomous multi-agent engineering team skill for Antigravity (AGY).
  Uses invoke_subagent to dispatch specialized engineering subagents in parallel
   across distinct files or modules, then integrates and verifies their changes.
  Use when the user runs /parallel-team or asks to remediate or build multiple
  components in parallel with a team of agents.
---

# Parallel Multi-Agent Engineering Team Skill (`/parallel-team`)

Coordinate a team of specialized autonomous subagents working in parallel via Antigravity's `invoke_subagent` tool, then run end-to-end verification.

## Workflow

1. **Partition Work by File / Module Boundary**:
   To prevent edit collisions, assign each subagent a clear, non-overlapping file or responsibility scope (or coordinate backend vs. frontend subagents in parallel):
   - **Backend Security, GDPR & Performance Subagent (`TypeName: "self"`, `Role: "Backend Security & Performance Engineer"`)**:
     Remediate `cymbal-control-tower/app.py`:
     1. Remove hardcoded `PAYMENT_GATEWAY_LIVE_SECRET`.
     2. Parameterize SQL queries (`?` placeholders) in `/api/incidents`.
     3. Mask `customer_iban` (e.g., `DE89 **** **** 00`) and `contact_email` (e.g., `l***@nordichome.de`) in API responses and logs.
     4. Remove `time.sleep(0.35)`, eliminate the $N+1$ query in `/api/sla-summary`, and compute `total_exposure_eur` as a numeric `float` sum.
     5. Enforce the €500 CFO governance gate in `/api/remediate` (raise HTTP 403 / `PENDING_EXECUTIVE_APPROVAL` if `credit_eur > 500` and `not req.manager_approved`).
   - **Frontend UI Subagent (`TypeName: "self"`, `Role: "Frontend Resilience Engineer"`)**:
     Remediate `cymbal-control-tower/static/dashboard.js`:
     1. Guard `maxCount` with `Math.max(..., 1)` so filtering an empty vertical never divides by zero (`NaN%`).
     2. Format `total_exposure_eur` cleanly with `Number(summary.total_exposure_eur || 0).toLocaleString()`.

2. **Dispatch Concurrently via `invoke_subagent`**:
   Launch the subagents in a single `invoke_subagent` tool call so they execute concurrently in the Subagents pane.

3. **Independent Verification**:
   After the subagents complete their edits, run the automated test suite (`python3 test_workshop_e2e.py`) to confirm 100% of security, GDPR, latency, UI, and governance checks pass.
