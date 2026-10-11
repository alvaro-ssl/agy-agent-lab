"""Cymbal Platform Reliability Control Tower — FastAPI service.

Internal dashboard that engineering leadership uses to track service health,
SLOs and error budgets, incidents, deploys and production change approvals.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db

APP_VERSION = "1.4.0"
LATENCY_BUDGET_MS = 300
FLEET_SLO_PCT = 99.9

app = FastAPI(title="Cymbal Platform Reliability Control Tower", version=APP_VERSION)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ApprovalDecision(BaseModel):
    decided_by: str = ""


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


@app.get("/")
def serve_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def team_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def cluster_replicas(service: str) -> int:
    """Live replica count from the cluster API."""
    time.sleep(0.25)  # cluster API round-trip
    with db.connect() as conn:
        return conn.execute("SELECT replicas FROM services WHERE service = ?", (service,)).fetchone()[0]


@app.get("/api/overview")
def overview(team: str = "") -> dict[str, Any]:
    conn = db.connect()
    query = """
        SELECT s.*, o.primary_on_call FROM services s JOIN on_call o ON o.team = s.team
    """
    params: list[Any] = []
    if team:
        query += " WHERE s.team = ?"
        params.append(team)
    query += " ORDER BY s.tier, s.service"

    services = []
    for svc in conn.execute(query, params).fetchall():
        name = svc["service"]
        latest = conn.execute(
            "SELECT requests, errors, p50_ms, p95_ms FROM metrics WHERE service = ? AND bucket = ?",
            (name, db.BUCKETS - 1),
        ).fetchone()
        p95_24h = []
        for hour in range(24):
            hour_values = []
            for bucket in range(hour * 12, hour * 12 + 12):
                row = conn.execute(
                    "SELECT p95_ms FROM metrics WHERE service = ? AND bucket = ?", (name, bucket)
                ).fetchone()
                hour_values.append(row["p95_ms"])
            p95_24h.append(round(max(hour_values), 1))
        deploy = conn.execute(
            "SELECT version, minutes_ago, result FROM deploys WHERE service = ? ORDER BY minutes_ago LIMIT 1",
            (name,),
        ).fetchone()
        incident = conn.execute(
            "SELECT incident_id, severity FROM incidents WHERE service = ? AND status != 'Resolved'", (name,)
        ).fetchone()

        availability = 100 * (1 - svc["errors_30d"] / svc["requests_30d"])
        allowed_errors = svc["requests_30d"] * (100 - svc["slo_availability_pct"]) / 100
        budget = 100 * (1 - svc["errors_30d"] / allowed_errors)
        rpm = round(latest["requests"] / db.BUCKET_MINUTES)
        services.append(
            {
                "service": name,
                "team": svc["team"],
                "tier": svc["tier"],
                "on_call": svc["primary_on_call"],
                "slo_availability_pct": svc["slo_availability_pct"],
                "availability_30d_pct": round(availability, 3),
                "error_budget_pct": round(budget, 1),
                "requests_per_min": f"{rpm:,}",
                "error_rate_pct": round(100 * latest["errors"] / max(1, latest["requests"]), 2),
                "p50_ms": latest["p50_ms"],
                "p95_ms": latest["p95_ms"],
                "p95_target_ms": svc["p95_target_ms"],
                "p95_24h": p95_24h,
                "replicas": cluster_replicas(name),
                "version": svc["version"],
                "last_deploy": (
                    {
                        "version": deploy["version"],
                        "at": db.minutes_ago_to_iso(deploy["minutes_ago"]),
                        "result": deploy["result"],
                    }
                    if deploy
                    else None
                ),
                "open_incident": dict(incident) if incident else None,
                "status": db._service_status(
                    budget, latest["p95_ms"], svc["p95_target_ms"], dict(incident) if incident else None
                ),
            }
        )
    teams = sorted({r["team"] for r in conn.execute("SELECT team FROM services")})
    conn.close()

    hourly = db.fleet_hourly()
    return {
        "version": APP_VERSION,
        "fleet_slo_pct": FLEET_SLO_PCT,
        "requests_per_min_24h": [h["requests_per_min"] for h in hourly],
        "error_rate_24h": [h["error_rate_pct"] for h in hourly],
        "teams": [{"name": t, "slug": team_slug(t)} for t in teams],
        "services": services,
    }


@app.get("/api/services/{service}/timeseries")
def service_timeseries(service: str) -> dict[str, Any]:
    svc = db.fetch_service(service)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service}'")
    # Latency is reported in seconds, matching our Prometheus metrics.
    points = [
        {**p, "p50_ms": round(p["p50_ms"] / 1000, 3), "p95_ms": round(p["p95_ms"] / 1000, 3)}
        for p in db.fetch_timeseries(service)
    ]
    return {
        "service": service,
        "p95_target_ms": svc["p95_target_ms"],
        "points": points,
        "deploys": [d for d in db.fetch_deploys(limit=50, service=service) if d["minutes_ago"] <= 24 * 60],
        "incidents": db.fetch_incidents(service=service),
    }


@app.get("/api/incidents")
def incidents(status: str = "all") -> list[dict[str, Any]]:
    return db.fetch_incidents(status=status)


@app.get("/api/deploys")
def deploys(limit: int = 12) -> list[dict[str, Any]]:
    return db.fetch_deploys(limit=limit)


@app.get("/api/approvals")
def approvals(status: str = "") -> list[dict[str, Any]]:
    return db.fetch_approvals(status=status)


@app.post("/api/approvals/{approval_id}/{decision}")
def decide(approval_id: str, decision: str, body: ApprovalDecision) -> dict[str, Any]:
    approval = db.fetch_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Unknown approval '{approval_id}'")
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")
    on_call = db.fetch_service(approval["service"])["primary_on_call"]
    return db.decide_approval(approval_id, decision == "approve", body.decided_by or on_call)


@app.get("/api/health")
def health() -> dict[str, Any]:
    # Lightweight probe for the load balancer: no database work on every check.
    return {"status": "OPERATIONAL", "version": APP_VERSION, "latency_budget_ms": LATENCY_BUDGET_MS}
