# Track 1: AGY — Google Antigravity Exercises

Welcome to **Track 1** of the CxO Leaders Exchange. Technical leaders direct autonomous engineering agents in **Google Antigravity (AGY)** — `/browser`, `/grill-me`, `/plan`, `/goal`, `/learn`, `/schedule` — and then build, red-team and govern a production operations agent with the **Google Agents CLI (`agents-cli` / ADK)** skills.

The two plays are independent:
- **Play 1** — Cymbal's **Platform Reliability Control Tower**, the internal dashboard leadership uses for the Monday ops review, broken by Friday's v1.4.0 release.
- **Play 2** — a synthetic, 8-layer **digital twin of the participant's own company**, and an autonomous agent built with `agents-cli` that analyses it and takes decisions, some alone and some only with an executive's approval.

---

## Directory Structure

> [!IMPORTANT]
> - **`agy_workspace/`** is the participant workspace. Copy it to each participant's laptop and **open this folder in Antigravity for both plays** (that is what loads the workspace rules and skills).
> - **`utils/`** is for facilitators only: setup, documentation, testing and the answer key.

```text
1-agy/
├── README.md                              # This file
├── agy_workspace/                         # OPEN THIS FOLDER IN ANTIGRAVITY (Play 1 & Play 2)
│   ├── AGENTS.md                          # How to run, test and reset both plays (read by Antigravity)
│   ├── requirements.txt                   # Python dependencies (fastapi, uvicorn, google-adk, google-genai, ...)
│   ├── .agents/
│   │   ├── rules/                         # cymbal-governance.md (performance, API contracts, rollbacks), deploying.md
│   │   └── skills/                        # browser, company-twin, decision-rights (custom), google-agents-cli-*, enable-a2ui, record-demo, ...
│   ├── cymbal-control-tower/              # Play 1: the Control Tower — own git repo, v1.3.0 (healthy) -> v1.4.0 (broken)
│   │   ├── app.py                         # FastAPI API
│   │   ├── database.py                    # SQLite schema + deterministic seed: 12 services, telemetry, incidents, deploys
│   │   ├── static/                        # Dashboard (index.html, styles.css, dashboard.js)
│   │   ├── tests/test_smoke.py            # The release pipeline's smoke tests (they pass on v1.4.0)
│   │   └── CHANGELOG.md                   # Release notes — context for the /grill-me trade-offs
│   ├── company-twin/                      # Play 2: the company digital twin
│   │   ├── company_profile.yaml           # The company the twin represents — reshaped to each participant's company
│   │   ├── generate_twin.py, archetypes.py# Builds the 8-layer twin (SQLite + CSVs + summary) for 6 industries
│   │   ├── decision_rights.yaml           # What the agent may decide alone / with which executive / never
│   │   ├── twin_tools.py                  # Agent tools: analyse, simulate, act (with human approvals)
│   │   └── inbox_app.py, static/          # Company Twin overview + Decision Inbox on :8090
│   └── eval-kit/                          # Play 2 Step 6: decision-governance eval (5 cases + deterministic metric)
└── utils/                                 # Facilitators only
    ├── lab-agy-gdoc.md                    # Executive briefing & copy-paste prompts for both plays
    ├── WORKSHOP_GUIDE.md                  # Run of show, timings and facilitator notes
    ├── project_brief.md                   # Brief for the Play 2 company analyst agent
    ├── setup-laptops.sh                   # Pre-session laptop setup (uv, .venv, agents-cli, skills, DB, git history)
    ├── cymbal-control-tower.bundle        # Git bundle with the v1.3.0 -> v1.4.0 history
    ├── run_agy_lab.sh                     # Runs every prompt in one Antigravity session on a throwaway copy
    ├── test_workshop_e2e.py               # Verifies the exercise is intact
    └── reference/                         # Answer keys, reference agent, example spec, Step 6 fix, screenshots
```

---

## Two Connected Plays (45–60 Min Cap)

| Play | Focus | Key commands & skills | Outcome |
| :--- | :--- | :--- | :--- |
| **Play 1 (15–20 min)** | **Command an autonomous engineering team** | `/browser`, `/grill-me`, `/plan`, `/goal` (parallel subagents), `/learn`, `/schedule` | See the broken dashboard, make the leadership trade-offs (roll back vs fix forward), get a plan, approve it into parallel backend/frontend subagents, verify with a real-browser screenshot, codify a release gate and watch it hold, schedule a CTO briefing. |
| **Play 2 (30 min)** | **An autonomous agent that runs your company's digital twin** | `/company-twin`, `/grill-me`, "Use agents-cli to build…" (workflow + scaffold), `/google-agents-cli-eval`, `/enable-a2ui`, `/record-demo` | Reshape the twin into your company, agree the agent's decision rights, build it with one sentence, let it find the root cause and act — alone where allowed, through the Decision Inbox where not — then red-team the human approvals and enforce them in code. |

---

## Quick Start

1. **Set up each laptop** (creates `agy_workspace/.venv`, installs dependencies and `agents-cli`, installs skills, seeds the Control Tower and restores its git history, generates the default company twin, checks for Chrome):
   ```bash
   bash 1-agy/utils/setup-laptops.sh
   ```
   Or just the Python environment:
   ```bash
   cd 1-agy/agy_workspace
   uv venv .venv --python 3.12 --seed      # or: python3 -m venv .venv  (Python 3.11-3.13)
   .venv/bin/pip install -r requirements.txt
   ```

2. **Verify the exercise** (runs on a temporary copy; never modifies `agy_workspace/`):
   ```bash
   1-agy/agy_workspace/.venv/bin/python 1-agy/utils/test_workshop_e2e.py
   ```

3. **Rehearse it with Antigravity** (every prompt, one session, throwaway copy):
   ```bash
   bash 1-agy/utils/run_agy_lab.sh --play=1        # or: --play=2 --company="Siemens"
   ```

4. **Run the workshop:** open `1-agy/agy_workspace` in Antigravity and follow [`utils/lab-agy-gdoc.md`](utils/lab-agy-gdoc.md). Facilitator notes and timings are in [`utils/WORKSHOP_GUIDE.md`](utils/WORKSHOP_GUIDE.md); the answer key is in [`utils/reference/README.md`](utils/reference/README.md).
