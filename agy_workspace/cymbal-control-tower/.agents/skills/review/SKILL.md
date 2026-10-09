---
name: review
description: >-
  Staff-Engineer code review and security/GDPR/performance audit skill for Antigravity (AGY).
  Use this skill when the user runs /review or asks for a thorough code review of a commit,
  diff (e.g., HEAD~1..HEAD), branch, or specific files to catch security vulnerabilities,
  GDPR/PII leaks, performance bottlenecks, and business-logic or governance flaws.
---

# Staff-Engineer Code Review Skill (`/review`)

Perform a rigorous, high-signal, read-only code review of the requested commit, diff, or files, and return a structured report.

## 1. Role & Read-Only Boundary
- **Read-only by default**: Your role during `/review` is to **audit and report**, not to modify code. Unless the user explicitly asks you to apply fixes in the same turn, do **NOT** modify workspace files or alter Git history.
- **Verify before reporting**: Use your terminal/search/file-reading tools (or delegate to a `research` / `self` subagent via `invoke_subagent`) to inspect the diff and surrounding callers before reporting an issue.

## 2. Review Methodology

### Step 1: Resolve Target Scope
1. If a commit range is specified (e.g. `HEAD~1..HEAD`), run `git show --stat` and `git diff HEAD~1..HEAD` inside the target project directory (e.g. `cymbal-control-tower/`).
2. If no commit range is specified, inspect uncommitted changes (`git status`, `git diff`) first, falling back to `git show HEAD` (`HEAD~1..HEAD`) if the working tree is clean.
3. Read the full files touched by the diff (`app.py`, `database.py`, `static/dashboard.js`, etc.) to audit system invariants beyond the diff lines.

### Step 2: Evaluate Substantive Defect Categories
Check every modified file across four executive risk dimensions:
1. **Security & Trust Boundaries (`P1`)**:
   - Hardcoded secrets, API keys, or live payment tokens (`sk_live_...`) in source code.
   - SQL injection vectors (string interpolation / f-strings in `cursor.execute(...)` instead of parameterized `?` bindings).
2. **Privacy & GDPR Compliance (`P1`)**:
   - Unmasked EU customer PII (`customer_iban`, `contact_email`) returned in API JSON responses or written to application logs.
3. **Performance & Reliability (`P1` / `P2`)**:
   - Artificial blocking delays (`time.sleep(...)`) or $O(N)$ / $N+1$ database queries inside request handlers.
   - Type/math errors in aggregations (e.g., string concatenation of numeric exposure values instead of `float` addition, or division-by-zero in frontend chart calculations when filtering empty subsets).
4. **Financial & Operational Governance (`P1`)**:
   - Missing policy enforcement gates (e.g., issuing SLA credits above `500.0` EUR without checking `manager_approved == True`).

## 3. Output Format

Return a structured Markdown review report containing:

1. **Verdict & Executive Summary**:
   - **Verdict**: `REQUEST CHANGES`, `APPROVE WITH SUGGESTIONS`, or `APPROVE`
   - 2–3 sentence summary of the commit reviewed and its operational risk.
2. **Findings (Ordered by Severity: `P1` Blocking -> `P2` Medium -> `P3` Low)**:
   - For each finding, include:
     - **Severity & Category** (e.g., `[P1 — Security / SQL Injection]`, `[P1 — GDPR PII Leak]`, `[P1 — CFO Governance Cap]`, `[P1 — Latency & Math Bug]`, `[P2 — Frontend Chart Bug]`)
     - **File & Line Range** (as clickable file links)
     - **Root Cause & Exploit/Failure Scenario**
     - **Recommended Fix Snippet**
