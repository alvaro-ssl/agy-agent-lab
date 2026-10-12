# Workshop workspace

## Projects

- `cymbal-control-tower/` — **Play 1.** The Platform Reliability Control Tower: FastAPI + SQLite + vanilla JS
  dashboard. It is its own git repository; `git log` shows the releases.
- `company-twin/` — **Play 2.** A synthetic, multi-layered digital twin of a company:
  - `company_profile.yaml` — the company the twin represents (edit it, then regenerate);
  - `generate_twin.py` — builds `data/twin.db`, `data/csv/` and `data/twin_summary.md` from the profile;
  - `decision_rights.yaml` — the chosen agent type, what it may decide alone, up to which limits, what needs
    which executive, and what is forbidden;
  - `twin_tools.py` — the agent's tools; `AGENT_TYPES` maps each of the four agent designs to its toolset;
  - `inbox_app.py` — the Company Twin overview and Decision Inbox where executives approve the agent's requests
    and read its reports.
- `twin-agent/` — created in Play 2 with `agents-cli` (not present until then).
- `eval-kit/` — reusable eval metrics for the Play 2 agent (`decision_guardrail_held`, a governance judge) and
  example cases; the eval dataset itself is written for the agent you chose.

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
- Work only inside this folder: never read, copy to or edit files in other folders (other copies of this
  workspace included).
- Never stop or kill a process you did not start in this conversation. If a port is busy, use the next free one
  (e.g. 8081, 8091), say so, and check `lsof -i :<port>` before blaming the IDE or the system.
- The twin is synthetic. It holds no people's names — leaders and owners are roles (e.g. Chief Operating Officer)
  and key accounts are segment labels. Never add names, in data, prompts, specs or replies.
- People decisions (performance, careers, compensation, hiring) are never taken by agents.
- Agents built here use the model `gemini-3.8-flash` (never the gemini-2.5 family), including eval judges.
- When you summarise what you built, quote the model and tool names exactly as they appear in the code.
- Play 1: verify the Control Tower in a real browser with a screenshot; put screenshots in `artifacts/`.
- Play 2: no screenshots. Print each local URL as a clickable link and open it (`open http://localhost:8090`,
  `open http://localhost:8080`).
