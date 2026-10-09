# Track 1: AGY — Google Antigravity Exercises

Welcome to **Track 1** of the CxO Leaders Exchange. This track focuses on executive-led autonomous engineering and production agent development using **Google Antigravity (AGY)**, built-in system slash commands (`/grill-me`, `/plan`, `/goal`, `/browser`, `/learn`, `/schedule`), multi-agent orchestration, and the **Google Agents CLI (`agents-cli` / ADK)** skills suite.

---

## Directory Structure

> [!IMPORTANT]
> - **`agy_workspace/`** is the participant workspace that **must be placed in each user's local directory** for the hands-on exercise.
> - **`utils/`** is **only needed for facilitator setup, documentation, and testing the exercise** (participants do not need `utils/` in their active workspace).

```text
1-agy/
├── README.md                              # Track 1 overview and quick start guide
├── agy_workspace/                         # REQUIRED in each user's local directory (Play 1 & Play 2 workspace)
│   ├── requirements.txt                   # Consolidated Python dependencies (fastapi, uvicorn, google-adk, google-genai, requests)
│   ├── .agents/                           # Workspace-wide AGY rules & 16 pre-installed skills
│   │   ├── rules/                         # cymbal-governance.md & deploying.md guardrails
│   │   └── skills/                        # google-agents-cli-*, enable-a2ui, executive-stress-test, etc.
│   ├── cymbal-control-tower/              # Play 1: FastAPI + SQLite + JS Live Operations & SLA Control Tower
│   │   ├── app.py                         # FastAPI service with seeded v1.4.0 regression for recovery
│   │   ├── database.py                    # SQLite incident & credit ledger schema + EMEA seed data
│   │   ├── dto_digital_twin.py            # 6-Layer Digital Twin of an Organization (DTO) & causal shock engine
│   │   ├── enterprise_tools.py            # 6 ADK function tools (incidents, live ECB FX, €500 cap, DTO, web/Search)
│   │   └── static/                        # Live executive telemetry dashboard (index.html, dashboard.js)
│   └── autonomous-ops-agent/              # Play 2: ADK Production Agent & Evaluation Suite
│       ├── app/agent.py                   # ADK agent wired with enterprise & DTO tools + sandbox simulation
│       └── tests/eval/                    # Trajectory + LLM-as-Judge €500 governance evaluation suite
└── utils/                                 # ONLY needed for testing & facilitator setup (not required by users)
    ├── WORKSHOP_GUIDE.md                  # Step-by-step Play 1 & Play 2 facilitator/participant guide
    ├── lab-agy-gdoc.md                    # Full executive briefing & copy-paste prompt script
    ├── project_brief.md                   # Cymbal EMEA Autonomous SLA & Incident War-Room Agent brief
    ├── setup-laptops.sh                   # Pre-session laptop bootstrap (uv, .venv, APIs, skills, SQLite, git history)
    ├── cymbal-control-tower.bundle        # Git bundle preserving the 2-commit v1.3.0 -> v1.4.0 regression history
    └── test_workshop_e2e.py               # Automated E2E verification suite for Play 1 & Play 2
```

---

## Two Connected Plays (45–60 Min Cap)

| Play | Focus | Working Directory | Key AGY Commands & Skills | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Play 1 (15 Mins)** | **Antigravity Power Tips & Tricks — Command an Autonomous Engineering Team** | [`agy_workspace/cymbal-control-tower/`](agy_workspace/cymbal-control-tower/) | `/grill-me`, `/plan`, `/goal` (parallel subagents), `/browser`, `/learn`, `/schedule` | Diagnose a faulty `v1.4.0` release (`git diff HEAD~1..HEAD`), align on recovery via interactive question cards, fan out parallel backend/frontend subagents in a closed verification loop, verify in Chrome, and codify GDPR + €500 governance rules. |
| **Play 2 (30 Mins)** | **Build a Production-Ready Agent with `agents-cli` & ADK** | [`agy_workspace/autonomous-ops-agent/`](agy_workspace/autonomous-ops-agent/) | `/google-agents-cli-scaffold`, `/google-agents-cli-adk-code`, `/google-agents-cli-eval`, `/enable-a2ui`, `/google-agents-cli-deploy`, `/record-demo` | Scaffold and test an ADK agent locally in the Playground (`http://localhost:8080`), run isolated Python sandbox SLA simulations & 6-Layer Digital Twin (DTO) causal shock propagation, enforce the €500 Board override guardrail via `agents-cli eval`, and render rich A2UI cards. |

---

## Quick Start

1. **Create the Local Virtualenv & Install Dependencies (inside `agy_workspace/`):**
   - **If `python3` (3.11+) is already installed:**
     ```bash
     cd 1-agy/agy_workspace
     python3 -m venv .venv
     .venv/bin/pip install -r requirements.txt
     ```
   - **If `python3` is NOT installed (or is older than 3.11 on macOS), use `uv` to auto-download standalone Python 3.12:**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH"
     cd 1-agy/agy_workspace
     uv venv .venv --python 3.12 --seed
     .venv/bin/pip install -r requirements.txt
     ```

2. **Or Run the Full Pre-Session Laptop Bootstrap (`utils/setup-laptops.sh`):**
   ```bash
   bash 1-agy/utils/setup-laptops.sh
   ```
   This automatically creates `1-agy/agy_workspace/.venv`, installs all dependencies (`requirements.txt`), ensures `uv` and `google-agents-cli` are installed, syncs `.agents/rules/` and `.agents/skills/`, initializes `cymbal_ops.db`, and restores the 2-commit Git history (`v1.3.0` → `v1.4.0`) inside `1-agy/agy_workspace/cymbal-control-tower/`.

3. **Verify Everything End-to-End (Testing Only):**
   ```bash
   python3 1-agy/utils/test_workshop_e2e.py
   ```

4. **Run the Workshop:**
   - Open [`1-agy/utils/WORKSHOP_GUIDE.md`](utils/WORKSHOP_GUIDE.md) or [`1-agy/utils/lab-agy-gdoc.md`](utils/lab-agy-gdoc.md) for the complete run-of-show and copy-paste prompts.
   - For **Play 1**, open `1-agy/agy_workspace/cymbal-control-tower` in Antigravity (`AGY`).
   - For **Play 2**, open `1-agy/agy_workspace` in Antigravity (`AGY`).
