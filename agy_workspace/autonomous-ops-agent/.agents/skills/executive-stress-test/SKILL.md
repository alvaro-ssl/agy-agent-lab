---
name: executive-stress-test
description: >-
  Multi-perspective executive architecture stress-test skill for Antigravity (AGY).
  Spawns parallel subagents (CTO Latency & Resilience lens, CISO & GDPR DPO lens,
  CFO Financial Governance lens) via invoke_subagent and synthesizes a unified,
  zero-regression remediation blueprint. Use when the user invokes /executive-stress-test
  or asks to stress-test an architecture from multiple executive perspectives.
---

# Executive Multi-Perspective Stress-Test Skill (`/executive-stress-test`)

When activated, stress-test the target system architecture in parallel from multiple executive viewpoints before writing production code.

## Workflow

1. **Launch Parallel Perspective Subagents (`invoke_subagent`)**:
   Call `invoke_subagent` in a **single tool call** with three concurrent `research` (or `self` read-only) subagents:
   - **Subagent 1 (`Role: "CTO Performance & Resilience Architect"`)**:
     Audit database queries, request latency bottlenecks (`time.sleep`, $N+1$ SQLite loops), numerical aggregation accuracy, and frontend rendering resilience. Propose concrete $<50\text{ms}$ query and UI fixes.
   - **Subagent 2 (`Role: "CISO & GDPR Data Protection Officer"`)**:
     Audit SQL injection surfaces, hardcoded secrets (`sk_live_...`), and EU customer PII exposure (`customer_iban`, `contact_email`) across API responses and logs. Propose parameterized SQL and deterministic PII masking helpers (`mask_iban`, `mask_email`).
   - **Subagent 3 (`Role: "CFO Financial Controls Auditor"`)**:
     Audit autonomous financial actions (`/api/remediate` and `credit_ledger`) against the €500 autonomous SLA credit cap. Define the exact HTTP 403 / `PENDING_EXECUTIVE_APPROVAL` guardrail contract when `credit_eur > 500` and `manager_approved` is false.

2. **Synthesize the Executive Blueprint**:
   Once all three subagents report back, synthesize their findings into a concise, prioritized **Zero-Regression Execution Blueprint** with:
   - **Executive Risk Matrix** (CTO / CISO & DPO / CFO findings)
   - **File-by-File Remediation Contract** (`app.py`, `static/dashboard.js`)
   - **Verification & Acceptance Criteria** (`test_workshop_e2e.py`)
