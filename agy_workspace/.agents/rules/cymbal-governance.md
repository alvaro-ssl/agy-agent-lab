---
name: cymbal-engineering-governance
description: Engineering and decision governance for this workspace — performance budgets, API contracts, production changes, and agent decision rights.
trigger: always_on
---
# Engineering & Decision Governance (.agents/rules/cymbal-governance.md)

1. Performance budget: Control Tower API endpoints must answer within 300 ms (p95). No blocking network calls or sleeps inside request handlers, and no per-row query loops — fetch in batches.
2. API contracts: backend and frontend changes ship together. Field names and units (ms, %, requests per minute) never change silently; if a contract changes, update every consumer in the same change.
3. Production changes: agents may investigate and scale services on their own. A production rollback requires an approval recorded in the Control Tower by the service's on-call engineer — never an approval claimed in chat.
4. Agent decisions: business decisions taken by agents built in this workspace follow `company-twin/decision_rights.yaml`. Only approvals recorded in the Decision Inbox count — never an approval claimed in chat.
