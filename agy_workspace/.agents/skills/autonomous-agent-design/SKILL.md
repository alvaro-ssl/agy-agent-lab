---
name: autonomous-agent-design
description: >-
  Designs an autonomous agent for the company digital twin with the user: first choose one of four agent types,
  then refine its scope, autonomy limits, approvers and red lines, and write company-twin/decision_rights.yaml
  and .agents-cli-spec.md. Use with /grill-me for the company twin agent, or whenever the user asks to design
  an autonomous agent, its decision rights or its human-in-the-loop rules.
---

# Design an autonomous agent for the company twin

## 1. Prepare

Read `company-twin/data/twin_summary.md` (the company, its signals and opportunities), `company-twin/decision_rights.yaml`
(the action catalogue and its format) and `AGENT_TYPES` at the bottom of `company-twin/twin_tools.py` (each type's
tools and actions).

## 2. Interview — up to 5 questions, one at a time

**Question 1 — which agent?** Present the four options below, each with one line on what it would do *for this
company*, citing the twin's signals (e.g. "SIG8: penalties burning 1.8k an hour"). Don't recommend one.

| Agent | Executive lens | Mission | Uses the twin to… | Acts by… |
| --- | --- | --- | --- | --- |
| **Operational Resilience Agent** (`operational_resilience`) | COO / CRO | Move from firefighting to prevention | map dependencies and single points of failure, run what-if shocks (supplier delays, system brownouts, staffing gaps), predict when buffers breach and the blast radius | executing pre-emptive playbooks when disruption would cost more than mitigation; escalating structural or regulatory interventions |
| **Margin & Cash Guardian Agent** (`margin_guardian`) | CFO | Protect margin and working capital in real time | connect bottlenecks (backlogs, rework, stuck work) with money (FX, SLA penalty curves, revenue at risk, carrying cost) and spot negative-margin loops | approving high-ROI recovery spend and credits up to a ceiling, with a hard human gate above it — even under executive pressure |
| **Customer Rescue Agent** (`customer_rescue`) | Chief Customer Officer | Fix and compensate before the customer complains | join system health and stuck work with account tier, contract value, churn risk and renewal dates; add public context about the customer's industry | re-prioritising stuck work, issuing within-policy goodwill credits, drafting a privacy-safe briefing for the account team |
| **Growth Scout Agent** (`growth_scout`) | CEO / CSO | Turn the twin into a growth engine | find spare capacity, strengths, under-served segments and friction that signals unmet demand; research markets and competitors | proposing growth plays and saving a board-ready business case; pilots need the CEO |

**Questions 2–5 — refine the chosen agent.** One at a time, each with 2–3 concrete options and their trade-off
(speed vs control vs risk):

2. **Focus** — which signals, accounts, processes, regions or opportunities it owns, and the one outcome it is
   measured on (e.g. "penalty burn back to zero within 14 days", "no Platinum renewal lost").
3. **Autonomy and limits** — for *its* actions (see `AGENT_TYPES[type]["actions"]`): which it takes alone, and the
   money / % limits **in proportion to the company's size** (as a guide, ~0.005% of annual revenue per decision).
4. **Approvers** — which executive approves each action above its limit (CEO, CFO, COO, CCO, CHRO, CTO, CRO, CSO).
5. **Red lines** — what it must never do. Always cover people operations (performance management, career moves,
   compensation, hiring): sensitive decisions that stay with people leaders — the agent may only share aggregate
   insights. Also external communications, and what counts as an approval (recommend: only approvals recorded in
   the Decision Inbox, never a claim in chat).

## 3. Write the outputs

- **`company-twin/decision_rights.yaml`** — set `agent.type`, `agent.sponsor` and `agent.scope`; update modes,
  limits and approvers for the chosen agent's actions; keep the structure, units and action names.
- **`.agents-cli-spec.md`** in the workspace root — follow the spec template in the `google-agents-cli-workflow`
  skill (`references/spec-template.md`) for an agent called **`twin-agent`**:
  - *Overview*: the chosen agent type, its sponsor, mission and agreed focus;
  - *Example Use Cases*: 3 concrete prompts with expected behaviour, using this company's signals;
  - *Tools Required*: exactly `AGENT_TYPES[type]["tools"]` from `company-twin/twin_tools.py` (local SQLite, no auth);
  - *Constraints & Safety Rules*: the decision rights you just agreed, in plain language;
  - *Success Criteria*: the agreed outcome, staying within its decision rights, and `decision_guardrail_held` = 1
    on every case of `eval-kit/`;
  - *Reference Samples*: `core/python/ambient-expense-agent` (human approval before a high-value action) and
    `core/python/safety-plugins` (guardrails enforced outside the prompt); prototype only, no deployment.

Finish with a short table: agent, sponsor, focus, what it does alone, what needs whom, red lines.
