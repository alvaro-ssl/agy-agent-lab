# Cymbal Platform Reliability Control Tower

Internal dashboard used by Cymbal engineering leadership for the weekly ops review
(Mondays 09:00 CET, chaired by the CTO): service health, SLOs and error budgets,
incidents, deploys, and production change approvals for the 12 services behind
cymbal.shop and the Cymbal apps. See `CHANGELOG.md` for releases.

## Run locally

```bash
../.venv/bin/uvicorn app:app --port 3000      # then open http://localhost:3000
../.venv/bin/pytest tests                     # smoke tests (run by the release pipeline)
```

The SQLite database (`cymbal_ops.db`) is created and seeded on startup.

## Layout

| Path | What it is |
| --- | --- |
| `app.py` | FastAPI service: `/api/overview`, `/api/services/{name}/timeseries`, `/api/incidents`, `/api/deploys`, `/api/approvals`, `/api/health` |
| `database.py` | Schema, deterministic seed data and query helpers |
| `static/` | Dashboard (`index.html`, `styles.css`, `dashboard.js`) |
| `tests/` | Smoke tests |
