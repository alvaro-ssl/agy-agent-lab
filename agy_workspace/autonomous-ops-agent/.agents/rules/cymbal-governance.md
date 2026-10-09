---
name: cymbal-emea-governance-rule
description: Mandatory GDPR PII redaction, parameterized SQL, and 500 EUR autonomous SLA credit cap for all Cymbal EMEA services and agents.
scope: workspace
---
# Cymbal EMEA Engineering & Financial Governance Rule (.agents/rules/cymbal-governance.md)
1. GDPR & PII Protection: Never log or return raw customer IBANs (`customer_iban`) or personal email addresses (`contact_email`) in API payloads, traces, or console logs. Always mask IBANs as `XX00 **** **** 0000`.
2. Database Security & Latency: Never use Python f-strings or string concatenation for SQL queries. Always use parameterized `?` placeholders and avoid N+1 query loops.
3. Autonomous Financial Cap (500 EUR): Any SLA remediation credit or refund exceeding 500.00 EUR strictly requires `manager_approved=True` (Human-in-the-Loop VP Finance sign-off).
