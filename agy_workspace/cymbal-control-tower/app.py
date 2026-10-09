"""Cymbal EMEA Operations Control Tower — FastAPI Service (v1.4.0 Bad Deployment).

NOTE FOR FACILITATORS (Option 1 — Bad Deployment / Service Outage Scenario):
This deployment commit (HEAD~1..HEAD) degraded the service and broke the live dashboard:
  1. [SERVICE DEGRADATION & CORRUPTED TELEMETRY]: `/api/sla-summary` & `/api/health` suffer from an N+1 SQLite query loop + blocking `time.sleep(0.35)` per row + string concatenation bug (`total_exposure = f"{total_exposure}{int(exposure)}"`), marking the service `503_DEGRADED`.
  2. [SECURITY / GDPR]: Hardcoded `PAYMENT_GATEWAY_LIVE_SECRET`, SQL injection in `account_filter`, and raw `customer_iban` & `contact_email` leaked in API responses and logs.
  3. [FINANCIAL GOVERNANCE]: `/api/remediate` dropped the €500 executive approval check, allowing unlimited autonomous refunds with `manager_approved=False`.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import DB_PATH, fetch_all_incidents, init_db, record_credit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cymbal-control-tower")

# ❌ BAD DEPLOYMENT REGRESSION 1: Hardcoded production secret in source code
PAYMENT_GATEWAY_LIVE_SECRET = "sk_live_cymbal_emea_99a8b7c6d5e4f3a2b1"

app = FastAPI(title="Cymbal EMEA Operations Control Tower", version="1.4.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RemediateRequest(BaseModel):
    incident_id: str
    amount_eur: float
    reason: str
    manager_approved: bool = False


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def serve_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    # ❌ Service reports degraded status due to bad v1.4.0 deployment
    return {
        "status": "503_SERVICE_DEGRADED",
        "healthy": False,
        "version": "1.4.0-broken",
        "reason": "Telemetry endpoint N+1 query bottleneck and unmasked PII regression",
    }


@app.get("/api/incidents")
def list_incidents(account_filter: str = "") -> list[dict[str, Any]]:
    """Returns active incidents.

    ❌ BAD DEPLOYMENT REGRESSION 2: Raw SQL string interpolation + unmasked IBAN/email PII leak.
    """
    if account_filter:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        query = f"SELECT * FROM incidents WHERE account_name LIKE '%{account_filter}%'"
        rows = [dict(r) for r in cur.execute(query).fetchall()]
        conn.close()
    else:
        rows = fetch_all_incidents()

    for r in rows:
        logger.info(
            "Loaded incident %s for %s (IBAN: %s, Email: %s)",
            r["incident_id"],
            r["account_name"],
            r["customer_iban"],
            r["contact_email"],
        )
        r["estimated_exposure_eur"] = round(
            (r["downtime_mins"] / 60.0) * r["penalty_rate_per_hr"], 2
        )
    return rows


@app.get("/api/sla-summary")
def get_sla_summary() -> dict[str, Any]:
    """Calculates SLA penalty exposure across EMEA verticals.

    ❌ BAD DEPLOYMENT REGRESSION 3: N+1 query loop + blocking sleep + string concatenation bug.
    """
    incidents = fetch_all_incidents()
    by_vertical: dict[str, str] = {}
    total_exposure = ""  # ❌ Bug: string concatenation instead of numeric float sum!

    for inc in incidents:
        time.sleep(0.35)
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT downtime_mins, penalty_rate_per_hr FROM incidents WHERE incident_id = ?",
            (inc["incident_id"],),
        )
        mins, rate = cur.fetchone()
        conn.close()

        exposure = round((mins / 60.0) * rate, 2)
        total_exposure = f"{total_exposure}{int(exposure)}"
        by_vertical[inc["vertical"]] = by_vertical.get(inc["vertical"], "") + str(int(exposure))

    return {
        "service_status": "503_SERVICE_DEGRADED",
        "total_exposure_eur": total_exposure,
        "by_vertical": by_vertical,
        "incident_count": len(incidents),
    }


@app.post("/api/remediate")
def remediate_incident(req: RemediateRequest) -> dict[str, Any]:
    """Issues an SLA credit to the customer's account.

    ❌ BAD DEPLOYMENT REGRESSION 4: Dropped the €500 executive approval check!
    """
    incidents = fetch_all_incidents()
    target = next((i for i in incidents if i["incident_id"] == req.incident_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Incident {req.incident_id} not found")

    return record_credit(
        incident_id=req.incident_id,
        account_name=target["account_name"],
        amount_eur=req.amount_eur,
        manager_approved=req.manager_approved,
        reason=req.reason,
    )
