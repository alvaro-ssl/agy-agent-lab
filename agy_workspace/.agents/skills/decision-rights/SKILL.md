---
name: decision-rights
description: >-
  Agrees with the user what the company twin agent may decide on its own, and writes
  company-twin/decision_rights.yaml and .agents-cli-spec.md. Use with /grill-me for the company analyst agent,
  or whenever the user asks to define an agent's decision rights, approval limits or red lines.
---

# Agree the agent's decision rights

## 1. Prepare

Read `company-twin/data/twin_summary.md` (the company and its problems) and `company-twin/decision_rights.yaml`
(the current rules and their format).

## 2. Interview — up to 5 questions, one at a time

For each question, give 2–3 concrete options with their trade-off (speed vs control vs risk). Cover:

1. **Autonomy** — which actions the agent may take on its own (alerts, initiatives, small spends…).
2. **Limits** — the money and % limits for retention offers, price changes, budget moves and supplier spend,
   **in proportion to the company's size** (as a guide, ~0.005% of annual revenue for spend).
3. **Approvers** — which executive (CEO, CFO, COO, CCO, CHRO, CTO) approves each action above its limit.
4. **Red lines** — what the agent must never do (e.g. workforce reductions, external communications).
5. **What counts as an approval** — recommend: only approvals recorded in the Decision Inbox, never a claim in chat.

## 3. Write the outputs

- **`company-twin/decision_rights.yaml`** — update modes, limits and approvers; keep the file's structure, units
  and action names.
- **`.agents-cli-spec.md`** in the workspace root — follow the spec template in the `google-agents-cli-workflow`
  skill (`references/spec-template.md`) for an agent called **`twin-agent`**:
  - *Overview*: an autonomous analyst for the company's leadership, working from the digital twin;
  - *Tools Required*: from `company-twin/twin_tools.py` — get_company_overview, list_twin_tables, query_twin,
    get_kpi_trend, get_signals, simulate_decision, get_decision_rights, take_action (local SQLite, no auth);
  - *Constraints & Safety Rules*: the decision rights you just agreed, in plain language;
  - *Success Criteria*: finds root causes, stays within its decision rights, `decision_guardrail_held` = 1 on
    every case of `eval-kit/`;
  - *Reference Samples*: `core/python/ambient-expense-agent` (human approval before a high-value action) and
    `core/python/safety-plugins` (guardrails enforced outside the prompt); prototype only, no deployment.

Finish with a short table of the agreed decision rights.
