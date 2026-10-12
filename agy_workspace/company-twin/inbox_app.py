"""Company Twin overview + Decision Inbox (http://localhost:8090).

Shows the digital twin at a glance, the approvals the agent is waiting for (approve or reject them as the named
executive), and the audit log of every action the agent has taken.

Run:  .venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090
"""

from __future__ import annotations

import sqlite3

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "twin.db"
STATIC = HERE / "static"

app = FastAPI(title="Company Twin & Decision Inbox")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "inbox.html")


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Twin not generated yet — run generate_twin.py")
    company = rows("SELECT * FROM company")[0]
    months = [r["month"] for r in rows("SELECT DISTINCT month FROM monthly_financials ORDER BY month")]
    last12, prev12 = months[-12:], months[-24:-12]
    fin = rows("SELECT * FROM monthly_financials")
    rev = sum(r["revenue"] for r in fin if r["month"] in last12)
    prev = sum(r["revenue"] for r in fin if r["month"] in prev12)
    ebitda = sum(r["ebitda"] for r in fin if r["month"] in last12)

    bus = []
    for bu in rows("SELECT * FROM business_units"):
        f = [r for r in fin if r["bu_id"] == bu["bu_id"]]
        r_now = sum(r["revenue"] for r in f if r["month"] in last12)
        r_prev = sum(r["revenue"] for r in f if r["month"] in prev12)
        bus.append({**bu, "revenue_last_12m": r_now, "growth_pct": round(100 * (r_now / r_prev - 1), 1),
                    "ebitda_margin_pct": round(100 * sum(r["ebitda"] for r in f if r["month"] in last12) / r_now, 1),
                    "monthly_revenue": [round(r["revenue"]) for r in sorted(f, key=lambda r: r["month"])]})

    segments = rows("SELECT * FROM customer_segments")
    org = rows("SELECT * FROM org_units")
    procs = rows("SELECT * FROM processes")
    sups = rows("SELECT * FROM suppliers")
    objectives = rows("SELECT * FROM objectives WHERE target IS NOT NULL")
    customers = sum(s["customers"] for s in segments)
    churn = sum(s["churn_monthly_pct"] * s["customers"] for s in segments) / customers
    headcount = sum(o["headcount"] for o in org)
    accounts = rows("SELECT * FROM accounts")
    at_risk = [a for a in accounts if a["renewal_in_days"] <= 60 and a["sla_hours_in_breach"] > 0]
    systems = rows("SELECT * FROM systems")
    fx = {r["currency"]: r["units_per_base"] for r in rows("SELECT currency, units_per_base FROM fx_rates WHERE month = (SELECT MAX(month) FROM fx_rates)")}
    burn = sum(a["sla_penalty_per_hour"] / fx.get(a["currency"], 1) for a in accounts if a["sla_hours_in_breach"] > 0)
    breaching_buffers = [b for b in rows("SELECT * FROM buffers") if b["days_to_breach"] is not None and b["days_to_breach"] <= 30]
    layers = [
        {"layer": "Strategy & objectives", "metric": f"{sum(o['status'] == 'at risk' for o in objectives)} of {len(objectives)} targets at risk · {len(rows('SELECT 1 FROM market_landscape'))} market plays mapped"},
        {"layer": "Organisation & people", "metric": f"{headcount:,} people · {sum(o['open_roles'] for o in org)} open roles"},
        {"layer": "Customers & market", "metric": f"{customers:,} customers · {len(accounts)} key accounts · {len(at_risk)} renewals at risk"},
        {"layer": "Products & services", "metric": f"{len(rows('SELECT 1 FROM product_lines'))} product lines"},
        {"layer": "Operations & processes", "metric": f"{len(procs)} processes · worst SLA {min(p['current_sla_attainment_pct'] for p in procs):.1f}% · {sum(s['single_point_of_failure'] for s in systems)} single point of failure"},
        {"layer": "Supply chain & assets", "metric": f"{len(sups)} suppliers · {sum(s['risk_score'] >= 60 for s in sups)} high risk · {len(rows('SELECT 1 FROM sites'))} sites"},
        {"layer": "Finance", "metric": f"EBITDA margin {100 * ebitda / rev:.1f}% vs {company['ebitda_margin_target_pct']}% · SLA penalties {company['currency']} {burn:,.0f}/h"},
        {"layer": "Risk & governance", "metric": f"{len(rows('SELECT 1 FROM risks'))} risks · {len(breaching_buffers)} buffers breach within 30 days"},
    ]
    rights = yaml.safe_load((HERE / "decision_rights.yaml").read_text())
    return {
        "company": company,
        "period": {"first": months[0], "last": months[-1]},
        "kpis": {
            "revenue_last_12m": rev, "growth_pct": round(100 * (rev / prev - 1), 1),
            "growth_target_pct": company["revenue_growth_target_pct"],
            "ebitda_margin_pct": round(100 * ebitda / rev, 1), "ebitda_margin_target_pct": company["ebitda_margin_target_pct"],
            "headcount": headcount, "customers": customers, "weighted_churn_pct": round(churn, 2),
        },
        "layers": layers,
        "business_units": bus,
        "signals": rows("SELECT * FROM signals ORDER BY severity = 'high' DESC, detected_days_ago"),
        "leadership": rows("SELECT * FROM leadership"),
        "agent": rights.get("agent", {}),
    }


@app.get("/api/approvals")
def approvals() -> list[dict[str, Any]]:
    return rows("SELECT * FROM approvals ORDER BY (status = 'PENDING') DESC, requested_at DESC")


@app.post("/api/approvals/{approval_id}/{decision}")
def decide(approval_id: str, decision: str) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")
    found = rows("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))
    if not found:
        raise HTTPException(status_code=404, detail=f"Unknown approval '{approval_id}'")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE approvals SET status = ?, decided_by = ?, decided_at = ? WHERE approval_id = ? AND status = 'PENDING'",
            ("APPROVED" if decision == "approve" else "REJECTED", found[0]["approver_name"],
             datetime.now(timezone.utc).isoformat(), approval_id),
        )
        conn.commit()
    finally:
        conn.close()
    return rows("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,))[0]


@app.get("/api/actions")
def actions() -> list[dict[str, Any]]:
    return rows("SELECT * FROM actions_log ORDER BY executed_at DESC")


@app.get("/api/reports")
def reports() -> list[dict[str, Any]]:
    return rows("SELECT * FROM reports ORDER BY created_at DESC")


@app.get("/reports/{report_id}", response_class=PlainTextResponse)
def report(report_id: str) -> str:
    found = rows("SELECT * FROM reports WHERE report_id = ?", (report_id,))
    if not found:
        raise HTTPException(status_code=404, detail=f"Unknown report '{report_id}'")
    return (HERE / found[0]["path"]).read_text()
