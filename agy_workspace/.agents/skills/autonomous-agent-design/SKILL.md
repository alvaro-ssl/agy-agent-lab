---
name: autonomous-agent-design
description: >-
  Designs an autonomous agent for the company digital twin with the user: first choose one of four agent types,
  then refine its scope, use cases, autonomy limits and human in the loop with questions specific to that agent,
  and write company-twin/decision_rights.yaml and .agents-cli-spec.md. Use with /grill-me for the company twin
  agent, or whenever the user asks to design an autonomous agent, its decision rights or its human-in-the-loop rules.
---

# Design an autonomous agent for the company twin

## 1. Prepare

Read `company-twin/data/twin_summary.md` (the company: what is going well, risks to watch, the opportunity),
`company-twin/decision_rights.yaml` (the action catalogue and its format) and `AGENT_TYPES` at the bottom of
`company-twin/twin_tools.py` (each type's tools, actions and human in the loop). Read each file once, whole.

## 2. Interview — 5 questions, one at a time

Keep every option to **one line** (under ~120 characters), cite at most one signal per option, and use roles,
never people's names (the twin has none). Quote this company's own units, processes, segments and numbers.

**Question 1 — which agent?** Present the four options, each with one line on what it would do *for this
company*. Don't recommend one.

| Agent | Human in the loop (process owner) | Mission |
| --- | --- | --- |
| **Operational Resilience Agent** (`operational_resilience`) | COO (operations), CTO for systems | Move from firefighting to prevention: stress-test operations, find single points of failure, act before disruptions cascade |
| **Margin & Cash Guardian Agent** (`margin_guardian`) | CFO | Protect margin and working capital: turn operational data into P&L impact and stop negative-margin loops |
| **Customer Rescue Agent** (`customer_rescue`) | Chief Customer Officer | Fix and compensate key accounts before they complain, and protect renewals |
| **Growth Scout Agent** (`growth_scout`) | Chief Strategy Officer, CEO for pilots | Pair spare capacity and strengths with market research to propose new revenue with a board-ready case |

**Questions 2–5 — specific to the chosen agent.** Use the question set for that agent below. Each question
offers 2–3 options built from this company's twin. Questions 2 and 3 are the leader's call — no recommendation;
for 4 and 5 you may mark one option "(suggested)".

### Operational Resilience Agent
2. **Scope** — what it protects first: the live supplier → process chain (SIG1 → SIG2); the system with no
   failover (SIG9); or the end-to-end customer-facing process (both). Plus the outcome it is measured on
   (e.g. "SLA back above target within 14 days").
3. **Use cases** — pick 2–3: a daily stress-test briefing for the COO; what-if shocks on request ("lose 50% of
   our critical supplier for 10 days"); running pre-agreed playbooks (defer non-critical work, expedite);
   preparing the capacity-and-failover case for the system.
4. **Autonomy and limits** — which playbooks it runs alone, and the money limit for expedites and capacity,
   in proportion to the company's size (as a guide, ~0.005% of annual revenue per decision).
5. **Human in the loop and red lines** — who approves above the limits (COO for operations and suppliers, CTO
   for systems), and what it must never do (see *Red lines* below).

### Margin & Cash Guardian Agent
2. **Scope** — which money it protects first: the hourly SLA-penalty and rework burn (SIG8); margin on the
   largest product lines; or working capital and currency exposure. Plus the outcome (e.g. "penalty burn back
   to zero within 14 days").
3. **Use cases** — pick 2–3: track the hourly burn and rank recovery options by NPV and payback; approve
   high-return recovery spend within its limit; a weekly margin-and-cash briefing for the CFO; check price or
   discount moves before they ship.
4. **Autonomy and limits** — recovery spend, credits and price moves it may approve alone, with money / %
   limits in proportion to the company's size; a hard human gate above them, even under executive pressure.
5. **Human in the loop and red lines** — who approves above the limits (CFO; COO for operational spend), and
   red lines.

### Customer Rescue Agent
2. **Scope** — which customers it looks after: the key accounts renewing within 60 days (SIG7); every key
   account with work outside SLA; or the segment whose churn is rising (SIG3). Plus the outcome (e.g. "no
   Platinum renewal lost this quarter").
3. **Use cases** — pick 2–3: re-prioritise stuck work for at-risk accounts; within-policy goodwill credits; a
   briefing for the account team before each renewal call (roles and segment labels only); a weekly at-risk
   renewals report.
4. **Autonomy and limits** — what it re-prioritises alone and the credit limit per account, in proportion to
   contract values (within each account's credit ceiling).
5. **Human in the loop and red lines** — who approves above the limit (Chief Customer Officer), and red lines —
   including no communication sent to customers directly.

### Growth Scout Agent
2. **Scope** — which growth lever: spare capacity plus a fast-growing adjacent market (SIG10); scaling what
   already works (SIG4, SIG6); or growing with the most loyal customers (SIG5). Plus the outcome (e.g. "one
   board-ready business case this quarter").
3. **Use cases** — pick 2–3: size and research a market; write a board-ready business case; propose a pilot
   with its budget and success measures; keep a watch on competitors.
4. **Autonomy and limits** — what it may do alone (research, initiatives, small capacity moves) and the
   limit for capacity it may re-allocate.
5. **Human in the loop and red lines** — who approves pilots and larger moves (CEO for pilots, CSO), and red lines.

### Red lines (always cover in question 5)
- People operations — performance management, career moves, compensation, hiring — stay with people leaders;
  the agent may only share aggregate insights.
- External communications.
- What counts as an approval: only approvals recorded in the Decision Inbox, never a claim in chat.

## 3. Write the outputs

- **`company-twin/decision_rights.yaml`** — set `agent.type`, `agent.sponsor` (the human in the loop) and
  `agent.scope`; update modes, limits and approvers for the chosen agent's actions; keep the structure, units
  and action names.
- **`.agents-cli-spec.md`** in the workspace root — follow the spec template in the `google-agents-cli-workflow`
  skill (`references/spec-template.md`) for an agent called **`twin-agent`**:
  - *Overview*: the agent type, its human in the loop, mission, agreed scope and outcome;
  - *Model*: `gemini-3.8-flash` (never the gemini-2.5 family);
  - *Example Use Cases*: the 2–3 use cases chosen in question 3, each as a concrete prompt with its expected
    behaviour, plus one above-limit request that must go to the human in the loop — these become the eval
    cases in Play 2 step 5;
  - *Tools Required*: exactly `AGENT_TYPES[type]["tools"]` from `company-twin/twin_tools.py` (local SQLite, no auth);
  - *Constraints & Safety Rules*: the decision rights you just agreed, in plain language;
  - *Success Criteria*: the agreed outcome, staying within its decision rights, and every eval case passing;
  - *Reference Samples*: `core/python/ambient-expense-agent` (human approval before a high-value action) and
    `core/python/safety-plugins` (guardrails enforced outside the prompt); prototype only, no deployment.

Finish with a short table: agent, human in the loop, scope, use cases, what it does alone, what needs whom, red lines.
