# Company digital twin

A synthetic, multi-layered digital twin of a company, reshaped to look like any real company from a short
profile, plus the tools an agent needs to analyse it and take decisions — some on its own, some only with an
executive's approval.

```text
company_profile.yaml ──generate_twin.py──▶ data/twin.db · data/csv/*.csv · data/twin_summary.md
                                                │
decision_rights.yaml ──▶ twin_tools.py ◀────────┘ ──▶ your agent (Play 2)
                                │
                          inbox_app.py  ──▶ http://localhost:8090  (overview · Decision Inbox · audit log)
```

| Layer | Tables |
| --- | --- |
| 1 Strategy & objectives | `company`, `business_units`, `objectives`, `leadership`, `regions` |
| 2 Organisation & people | `org_units` |
| 3 Customers & market | `customer_segments` |
| 4 Products & services | `product_lines` |
| 5 Operations & processes | `processes` |
| 6 Supply chain & assets | `suppliers`, `sites` |
| 7 Finance | `monthly_financials` (24 months, budget vs actual) |
| 8 Risk & governance | `risks`, `policies` |
| History & anomalies | `monthly_kpis` (24 months, long format), `signals` |
| Decisions | `approvals`, `actions_log` |

Industries: `retail_consumer`, `telecom`, `financial_services`, `industrial_manufacturing`, `energy_utilities`,
`software_saas` (see `archetypes.py`). The same profile always produces the same twin. Leadership and manager
names are generated — the twin never contains real people's names.

## Use it (from the `agy_workspace/` root)

```bash
.venv/bin/python company-twin/generate_twin.py                        # rebuild data/ from the profile
.venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090     # overview + Decision Inbox
```

Regenerating the twin resets approvals and the audit log; it never touches `decision_rights.yaml`.
