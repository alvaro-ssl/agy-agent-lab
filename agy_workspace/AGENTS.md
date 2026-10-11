# Workshop workspace

## Projects

- `cymbal-control-tower/` — **Play 1.** The Platform Reliability Control Tower: FastAPI + SQLite + vanilla JS
  dashboard. It is its own git repository; `git log` shows the releases.
- `company-twin/` — **Play 2.** A synthetic, multi-layered digital twin of a company:
  - `company_profile.yaml` — the company the twin represents (edit it, then regenerate);
  - `generate_twin.py` — builds `data/twin.db`, `data/csv/` and `data/twin_summary.md` from the profile;
  - `decision_rights.yaml` — what the agent may decide alone, up to which limits, what needs which executive,
    and what is forbidden;
  - `twin_tools.py` — the agent's tools (analyse, simulate, act);
  - `inbox_app.py` — the Company Twin overview and Decision Inbox where executives approve the agent's requests.
- `twin-agent/` — created in Play 2 with `agents-cli` (not present until then).
- `eval-kit/` — decision-governance eval dataset and metrics for the Play 2 agent.

## Commands (run from this folder)

- Python environment: `.venv/` in this folder. Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/uvicorn`.
- Control Tower (Play 1): `cd cymbal-control-tower && ../.venv/bin/uvicorn app:app --port 3000` → http://localhost:3000
- Control Tower smoke tests: `cd cymbal-control-tower && ../.venv/bin/pytest tests`
- Reset the Control Tower database: `cd cymbal-control-tower && ../.venv/bin/python -c "import database; database.init_db(force=True)"`
- Generate the company twin (Play 2): `.venv/bin/python company-twin/generate_twin.py`
- Company Twin & Decision Inbox: `.venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090` → http://localhost:8090
- Visual check in a real browser: the `browser` skill (`/browser`), or
  `.venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:3000`
  (add `--summary generic` for pages other than the Control Tower)

## Conventions

- Ports: 3000 Control Tower · 8080 agent Playground · 8090 Company Twin & Decision Inbox.
- The twin is synthetic. Never put real people's names in `company_profile.yaml`; leadership names are generated.
- Put screenshots and other verification output in `artifacts/`.
