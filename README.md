# AGY — Google Antigravity Exercises

Technical leaders direct autonomous engineering agents in **Google Antigravity (AGY)** — `/browser`, `/plan`, `/goal`, `/learn`, `/schedule` — and then design, build and evaluate an autonomous agent for their own company with the **Google Agents CLI (`agents-cli` / ADK)** skills.

The two plays are independent:
- **Play 1** — the reporting system is down: Cymbal's **Platform Reliability Control Tower**, the system leadership runs the business on, knocked out by Friday's v1.4.0 release.
- **Play 2** — a synthetic, 8-layer **digital twin of the participant's own company** (a balanced picture: strengths, risks to watch, an opportunity; roles and segment labels, no names), and one of four autonomous agents (Operational Resilience · Margin & Cash Guardian · Customer Rescue · Growth Scout) designed with `/grill-me`, built with `agents-cli` on Gemini 3.8 Flash, and taking decisions — some alone, some only with the approval of its human in the loop (the process owner).

---

## The workspace

> [!IMPORTANT]
> **`agy_workspace/`** is the participant workspace. **Open this folder in Antigravity for both plays** — that is what loads the workspace rules and skills.

```text
agy_workspace/                         # OPEN THIS FOLDER IN ANTIGRAVITY (Play 1 & Play 2)
├── AGENTS.md                          # How to run, test and reset both plays (read by Antigravity)
├── requirements.txt                   # Python dependencies (fastapi, uvicorn, google-adk, google-genai, ...)
├── .agents/
│   ├── rules/                         # cymbal-governance.md (performance, API contracts, rollbacks), deploying.md
│   └── skills/                        # custom: browser, company-twin, autonomous-agent-design; google-agents-cli-*, enable-a2ui, setup-memory-bank, ...
├── cymbal-control-tower/              # Play 1: the Control Tower — own git repo, v1.3.0 (healthy) -> v1.4.0 (broken)
│   ├── app.py                         # FastAPI API
│   ├── database.py                    # SQLite schema + deterministic seed: 12 services, telemetry, incidents, deploys
│   ├── static/                        # Dashboard (index.html, styles.css, dashboard.js)
│   ├── tests/test_smoke.py            # The release pipeline's smoke tests (they pass on v1.4.0)
│   └── CHANGELOG.md                   # Release notes — context for the fix-forward vs roll-back call
├── company-twin/                      # Play 2: the company digital twin
│   ├── company_profile.yaml           # The company the twin represents — reshaped to each participant's company
│   ├── generate_twin.py, archetypes.py# Builds the 8-layer twin (SQLite + CSVs + summary) for 6 industries
│   ├── decision_rights.yaml           # What the agent may decide alone / with its human in the loop / never
│   ├── twin_tools.py                  # Agent tools and the four agent types' toolsets (resilience, margin, customer, growth)
│   └── inbox_app.py, static/          # Company Twin overview + Decision Inbox on :8090
└── eval-kit/                          # Play 2 step 5: eval metrics + example cases
```

`twin-agent/` appears in the workspace during Play 2, when `agents-cli` builds the agent.

---

## Two Independent Plays (45–60 Min Cap)

| Play | Focus | Key commands & skills | Outcome |
| :--- | :--- | :--- | :--- |
| **Play 1 (15 min)** | **Command an autonomous engineering team** | `/browser` (custom skill), `/plan`, `/goal` (parallel subagents), `/learn`, `/schedule` (optional) | See and diagnose the broken dashboard, get a plan, approve it into parallel backend/frontend subagents, verify with a real-browser screenshot, add a release gate to enforce governance next time and watch it hold, optionally schedule a CTO briefing. |
| **Play 2 (30 min)** | **Design and build an autonomous agent for your company's digital twin** | `/company-twin`, `/grill-me`, "Use agents-cli to build…" (workflow + scaffold), `/google-agents-cli-eval`, `/enable-a2ui`, `/memory-bank-setup` | Reshape the twin into your company, pick and design one of four agents, build it with one sentence, let it work — alone where allowed, through its human in the loop in the Decision Inbox where not — then evaluate it with agents-cli on its own use cases and decision rights; optionally add executive cards (A2UI), long-term memory and deployment. |

---

## Quick Start

Laptops are set up before the session. Minimal setup, for reference:

```bash
uv tool install "google-agents-cli~=1.7.0" && agents-cli setup
cd 1-agy/agy_workspace
uv venv .venv --python 3.12 --seed && .venv/bin/pip install -r requirements.txt
.venv/bin/python company-twin/generate_twin.py
```

Already have an older `agents-cli`? Upgrade with `uv tool install --force "google-agents-cli~=1.7.0"`. Agents CLI
also needs Google credentials for Gemini: `gcloud auth application-default login` (or a `GEMINI_API_KEY`).

Then open the workspace in either surface:

- **Terminal:** `cd 1-agy/agy_workspace && agy --dangerously-skip-permissions`
- **AGY 2.0 (desktop app):** select `1-agy/agy_workspace` as the folder.

Commands to run, test and reset each play (ports 3000 Control Tower · 8080 agent Playground · 8090 Decision
Inbox) are in [`agy_workspace/AGENTS.md`](agy_workspace/AGENTS.md).
