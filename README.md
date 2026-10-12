# Track 1: AGY — Google Antigravity Exercises

Welcome to **Track 1** of the CxO Leaders Exchange. Technical leaders direct autonomous engineering agents in **Google Antigravity (AGY)** — `/browser`, `/plan`, `/goal`, `/learn`, `/schedule` — and then build, red-team and govern a production operations agent with the **Google Agents CLI (`agents-cli` / ADK)** skills.

The two plays are independent:
- **Play 1** — the reporting system is down: Cymbal's **Platform Reliability Control Tower**, the system leadership runs the business on, knocked out by Friday's v1.4.0 release.
- **Play 2** — a synthetic, 8-layer **digital twin of the participant's own company**, and one of four autonomous agents (Operational Resilience · Margin & Cash Guardian · Customer Rescue · Growth Scout) designed with `/grill-me`, built with `agents-cli`, and taking decisions — some alone, some only with an executive's approval.

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
│   │   └── skills/                        # browser, company-twin, autonomous-agent-design (custom), google-agents-cli-*, enable-a2ui, setup-memory-bank, ...
│   ├── cymbal-control-tower/              # Play 1: the Control Tower — own git repo, v1.3.0 (healthy) -> v1.4.0 (broken)
│   │   ├── app.py                         # FastAPI API
│   │   ├── database.py                    # SQLite schema + deterministic seed: 12 services, telemetry, incidents, deploys
│   │   ├── static/                        # Dashboard (index.html, styles.css, dashboard.js)
│   │   ├── tests/test_smoke.py            # The release pipeline's smoke tests (they pass on v1.4.0)
│   │   └── CHANGELOG.md                   # Release notes — context for the fix-forward vs roll-back call
│   ├── company-twin/                      # Play 2: the company digital twin
│   │   ├── company_profile.yaml           # The company the twin represents — reshaped to each participant's company
│   │   ├── generate_twin.py, archetypes.py# Builds the 8-layer twin (SQLite + CSVs + summary) for 6 industries
│   │   ├── decision_rights.yaml           # What the agent may decide alone / with which executive / never
│   │   ├── twin_tools.py                  # Agent tools and the four agent types' toolsets (resilience, margin, customer, growth)
│   │   └── inbox_app.py, static/          # Company Twin overview + Decision Inbox on :8090
│   └── eval-kit/                          # Play 2 Step 5: decision-governance eval (5 cases + deterministic metric)
└── utils/                                 # Facilitators only
    ├── lab-agy-gdoc.md                    # Executive briefing & copy-paste prompts for both plays
    ├── WORKSHOP_GUIDE.md                  # Run of show, timings and facilitator notes
    ├── project_brief.md                   # Brief for the Play 2 company analyst agent
    ├── setup-laptops.sh                   # Pre-session laptop setup (uv, .venv, agents-cli, skills, DB, git history)
    ├── cymbal-control-tower.bundle        # Git bundle with the v1.3.0 -> v1.4.0 history
    ├── run_agy_lab.sh                     # Runs every prompt in one Antigravity session on a throwaway copy
    ├── test_workshop_e2e.py               # Verifies the exercise is intact
    └── reference/                         # Answer keys, reference agent, example spec, Step 5 fix, screenshots
```

---

## Two Connected Plays (45–60 Min Cap)

| Play | Focus | Key commands & skills | Outcome |
| :--- | :--- | :--- | :--- |
| **Play 1 (15 min)** | **Command an autonomous engineering team** | `/browser`, `/plan`, `/goal` (parallel subagents), `/learn`, `/schedule` (optional) | See and diagnose the broken dashboard, get a plan, approve it into parallel backend/frontend subagents, verify with a real-browser screenshot, add a release gate to enforce governance next time and watch it hold, optionally schedule a CTO briefing. |
| **Play 2 (30 min)** | **Design and build an autonomous agent for your company's digital twin** | `/company-twin`, `/grill-me`, "Use agents-cli to build…" (workflow + scaffold), `/google-agents-cli-eval`, `/enable-a2ui`, `/memory-bank-setup` | Reshape the twin into your company, pick and design one of four agents, build it with one sentence, let it work — alone where allowed, through the Decision Inbox where not — then red-team the human approvals and enforce them in code; optionally add executive cards and long-term memory. |

---

## Quick Start

1. **Set up each laptop** (creates `agy_workspace/.venv`, installs dependencies, installs `agents-cli` 1.7.x and its skills, seeds the Control Tower and restores its git history, generates the default company twin, checks for Chrome):
   ```bash
   bash 1-agy/utils/setup-laptops.sh
   ```
   Or step by step:
   ```bash
   # uv (skip if installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH"

   # Google Agents CLI, pinned to the version the workspace's google-agents-cli-* skills target
   uv tool install "google-agents-cli~=1.7.0"
   agents-cli --version          # expect 1.7.x
   agents-cli setup              # installs the agents-cli skills for your coding agents

   # Python environment for both plays
   cd 1-agy/agy_workspace
   uv venv .venv --python 3.12 --seed      # or: python3 -m venv .venv  (Python 3.11-3.13)
   .venv/bin/pip install -r requirements.txt

   # Play 1 history and database, Play 2 twin
   git clone ../utils/cymbal-control-tower.bundle cymbal-control-tower/.git-tmp \
     && mv cymbal-control-tower/.git-tmp/.git cymbal-control-tower/.git && rm -rf cymbal-control-tower/.git-tmp
   (cd cymbal-control-tower && git checkout -f main && ../.venv/bin/python -c "import database; database.init_db(force=True)")
   .venv/bin/python company-twin/generate_twin.py
   ```
   Already have an older `agents-cli`? Upgrade with `uv tool install --force "google-agents-cli~=1.7.0"`. Agents
   CLI also needs Google credentials for Gemini: `gcloud auth application-default login` (or a `GEMINI_API_KEY`).

2. **Verify the exercise** (runs on a temporary copy; never modifies `agy_workspace/`):
   ```bash
   1-agy/agy_workspace/.venv/bin/python 1-agy/utils/test_workshop_e2e.py
   ```

3. **Rehearse it with Antigravity** (every prompt, one session, throwaway copy):
   ```bash
   bash 1-agy/utils/run_agy_lab.sh --play=1        # or: --play=2 --company="Siemens"
   ```

4. **Run the workshop:** open `1-agy/agy_workspace` in Antigravity and follow [`utils/lab-agy-gdoc.md`](utils/lab-agy-gdoc.md). Facilitator notes and timings are in [`utils/WORKSHOP_GUIDE.md`](utils/WORKSHOP_GUIDE.md); the answer key is in [`utils/reference/README.md`](utils/reference/README.md).
