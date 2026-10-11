"""SQLite storage, deterministic seed data and query helpers for the Cymbal Platform Reliability Control Tower.

The database models the internal platform that Cymbal's engineering teams run:
services with SLOs, 24 hours of 5-minute telemetry, incidents, deploys, on-call
rotations, and production change approvals.

Timestamps are stored as offsets ("minutes ago" / bucket index) and rendered
relative to the current time, so the dashboard always looks live.
"""

from __future__ import annotations

import math
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "cymbal_ops.db"

BUCKET_MINUTES = 5
BUCKETS = 288  # 24 hours of 5-minute buckets; bucket 287 is the most recent
SEED = 20261009
REGENERATE_AFTER_HOURS = 2

# (service, team, tier, slo_availability_pct, p95_target_ms, base_rpm, base_p50_ms,
#  base_p95_ms, base_error_rate_pct, replicas, version, previous_version, budget_consumed)
SERVICES = [
    ("storefront-web", "Storefront", 1, 99.90, 400, 9800, 118, 310, 0.05, 24, "v5.18.2", "v5.18.1", 0.42),
    ("checkout-api", "Checkout", 1, 99.95, 300, 2600, 92, 228, 0.03, 18, "v3.42.0", "v3.41.3", 0.31),
    ("payments-gateway", "Payments", 1, 99.99, 250, 1900, 74, 190, 0.004, 16, "v8.7.1", "v8.7.0", 0.64),
    ("identity-auth", "Identity", 1, 99.95, 150, 6400, 38, 96, 0.02, 12, "v2.9.4", "v2.9.3", 0.18),
    ("search-api", "Search & Discovery", 2, 99.90, 200, 7400, 61, 152, 0.04, 14, "v2.31.0", "v2.30.4", 0.55),
    ("catalog-service", "Search & Discovery", 2, 99.90, 180, 5200, 44, 121, 0.03, 10, "v6.3.0", "v6.2.7", 0.22),
    ("pricing-engine", "Pricing", 2, 99.90, 120, 4100, 21, 64, 0.02, 8, "v1.27.3", "v1.27.2", 0.12),
    ("inventory-sync", "Fulfilment", 2, 99.50, 500, 1200, 140, 380, 0.15, 6, "v4.5.2", "v4.5.1", 1.12),
    ("order-pipeline", "Fulfilment", 1, 99.90, 800, 2100, 260, 610, 0.05, 10, "v7.11.0", "v7.10.2", 0.47),
    ("notifications", "Customer Comms", 3, 99.50, 1000, 3300, 180, 520, 0.08, 6, "v3.3.1", "v3.3.0", 0.29),
    ("mobile-bff", "Mobile", 1, 99.90, 350, 5600, 88, 240, 0.04, 12, "v4.12.1", "v4.11.6", 0.38),
    ("data-ingest", "Data Platform", 3, 99.00, 2000, 900, 420, 1350, 0.30, 4, "v0.48.0", "v0.47.2", 0.71),
]

# (team, primary_on_call, secondary_on_call, slack_channel)
ON_CALL = [
    ("Storefront", "Lena Kovacs", "Ravi Menon", "#storefront-oncall"),
    ("Checkout", "Tomás Rivera", "Ines Duarte", "#checkout-oncall"),
    ("Payments", "Priya Nair", "Jonas Berg", "#payments-oncall"),
    ("Identity", "Kwame Asante", "Mia Schneider", "#identity-oncall"),
    ("Search & Discovery", "Aiko Tanaka", "Marco De Luca", "#search-oncall"),
    ("Pricing", "Hannah Weber", "Luis Ortega", "#pricing-oncall"),
    ("Fulfilment", "Sofia Marino", "Omar Haddad", "#fulfilment-oncall"),
    ("Customer Comms", "Elif Yilmaz", "Ben Carter", "#comms-oncall"),
    ("Mobile", "Noah Fischer", "Chloé Martin", "#mobile-oncall"),
    ("Data Platform", "Anya Petrova", "Daniel Okafor", "#data-oncall"),
]

# (incident_id, severity, title, service, commander, status, started_min_ago, resolved_min_ago or None)
INCIDENTS = [
    ("INC-2423", "SEV3", "Delayed order-confirmation emails (provider throttling)", "notifications", "Elif Yilmaz", "Monitoring", 62, None),
    ("INC-2421", "SEV2", "Stock levels lagging — warehouse feed backlog", "inventory-sync", "Sofia Marino", "Investigating", 172, None),
    ("INC-2419", "SEV3", "Search p95 latency regression after v2.31.0", "search-api", "Aiko Tanaka", "Identified", 300, None),
    ("INC-2417", "SEV1", "Card authorisations timing out at 3-D Secure provider", "payments-gateway", "Priya Nair", "Resolved", 192, 150),
    ("INC-2412", "SEV3", "Promo code validation errors at checkout", "checkout-api", "Tomás Rivera", "Resolved", 610, 585),
    ("INC-2409", "SEV2", "iOS app login loop after mobile-bff v4.12.0", "mobile-bff", "Noah Fischer", "Resolved", 925, 880),
    ("INC-2402", "SEV3", "Recommendation carousel empty on product pages", "catalog-service", "Marco De Luca", "Resolved", 1990, 1930),
    ("INC-2398", "SEV2", "Order export to ERP stalled overnight", "order-pipeline", "Omar Haddad", "Resolved", 2870, 2715),
]

# (service, version, team, author, minutes_ago, result)
DEPLOYS = [
    ("notifications", "v3.3.1", "Customer Comms", "ben.carter", 48, "succeeded"),
    ("pricing-engine", "v1.27.3", "Pricing", "luis.ortega", 95, "succeeded"),
    ("storefront-web", "v5.18.2", "Storefront", "ravi.menon", 140, "succeeded"),
    ("catalog-service", "v6.3.0", "Search & Discovery", "marco.deluca", 205, "succeeded"),
    ("inventory-sync", "v4.5.2", "Fulfilment", "omar.haddad", 238, "succeeded"),
    ("checkout-api", "v3.42.0", "Checkout", "ines.duarte", 330, "succeeded"),
    ("search-api", "v2.31.0", "Search & Discovery", "aiko.tanaka", 382, "succeeded"),
    ("identity-auth", "v2.9.4", "Identity", "mia.schneider", 455, "succeeded"),
    ("order-pipeline", "v7.11.0", "Fulfilment", "sofia.marino", 540, "succeeded"),
    ("payments-gateway", "v8.7.1", "Payments", "jonas.berg", 690, "succeeded"),
    ("mobile-bff", "v4.12.1", "Mobile", "chloe.martin", 862, "succeeded"),
    ("mobile-bff", "v4.12.0", "Mobile", "noah.fischer", 940, "rolled_back"),
    ("data-ingest", "v0.48.0", "Data Platform", "anya.petrova", 1010, "succeeded"),
    ("storefront-web", "v5.18.1", "Storefront", "lena.kovacs", 1150, "succeeded"),
    ("checkout-api", "v3.41.3", "Checkout", "tomas.rivera", 1295, "failed"),
]

# Telemetry stories layered over the baseline: (service, start_min_ago, end_min_ago, p95_mult, err_pct, rpm_mult)
TELEMETRY_EVENTS = [
    ("payments-gateway", 192, 150, 4.6, 3.8, 0.9),
    ("inventory-sync", 172, 0, 2.1, 1.9, 1.0),
    ("search-api", 382, 0, 1.75, 0.09, 1.0),
    ("notifications", 62, 0, 1.6, 0.6, 1.0),
    ("checkout-api", 610, 585, 1.3, 1.4, 1.0),
    ("mobile-bff", 940, 880, 1.8, 2.6, 0.95),
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now_bucket() -> datetime:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return now - timedelta(minutes=now.minute % BUCKET_MINUTES)


def minutes_ago_to_iso(minutes_ago: float) -> str:
    return (_now_bucket() - timedelta(minutes=minutes_ago)).isoformat()


def bucket_to_iso(bucket: int) -> str:
    return minutes_ago_to_iso((BUCKETS - 1 - bucket) * BUCKET_MINUTES)


def _diurnal(hour: float) -> float:
    """Traffic shape for a European consumer business: trough ~04:00, peak ~20:00, lunch bump."""
    day = 0.5 - 0.5 * math.cos(2 * math.pi * (hour - 4) / 24)
    evening = 0.35 * math.exp(-((hour - 20.5) ** 2) / 6.0)
    lunch = 0.15 * math.exp(-((hour - 12.5) ** 2) / 2.0)
    return 0.12 + 0.88 * (day + evening + lunch) / 1.1


def _generate_metrics(anchor: datetime) -> list[tuple]:
    rng = random.Random(SEED)
    rows = []
    for svc in SERVICES:
        name, _, _, _, _, base_rpm, base_p50, base_p95, base_err, *_ = svc
        events = [e for e in TELEMETRY_EVENTS if e[0] == name]
        for bucket in range(BUCKETS):
            minutes_ago = (BUCKETS - 1 - bucket) * BUCKET_MINUTES
            t = anchor - timedelta(minutes=minutes_ago)
            load = _diurnal((t.hour + t.minute / 60 + 2) % 24)  # UTC -> CEST
            rpm = base_rpm * load * rng.uniform(0.95, 1.05)
            p50 = base_p50 * (0.9 + 0.25 * load) * rng.uniform(0.94, 1.06)
            p95 = base_p95 * (0.88 + 0.3 * load) * rng.uniform(0.92, 1.1)
            err_pct = base_err * rng.uniform(0.6, 1.4)
            for _, start, end, p95_mult, ev_err, rpm_mult in events:
                if end <= minutes_ago <= start:
                    p95 *= p95_mult
                    p50 *= 1 + (p95_mult - 1) * 0.45
                    err_pct = max(err_pct, ev_err * rng.uniform(0.8, 1.2))
                    rpm *= rpm_mult
            requests = int(rpm * BUCKET_MINUTES)
            errors = int(round(requests * err_pct / 100))
            rows.append((name, bucket, requests, errors, round(p50, 1), round(p95, 1)))
    return rows


def init_db(force: bool = False) -> None:
    """Creates and seeds the database. Telemetry is regenerated when it is older than a few hours."""
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    conn = connect()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS services (
            service TEXT PRIMARY KEY,
            team TEXT NOT NULL,
            tier INTEGER NOT NULL,
            slo_availability_pct REAL NOT NULL,
            p95_target_ms INTEGER NOT NULL,
            replicas INTEGER NOT NULL,
            version TEXT NOT NULL,
            previous_version TEXT NOT NULL,
            requests_30d INTEGER NOT NULL,
            errors_30d INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metrics (
            service TEXT NOT NULL,
            bucket INTEGER NOT NULL,
            requests INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            p50_ms REAL NOT NULL,
            p95_ms REAL NOT NULL,
            PRIMARY KEY (service, bucket)
        );
        CREATE TABLE IF NOT EXISTS on_call (
            team TEXT PRIMARY KEY,
            primary_on_call TEXT NOT NULL,
            secondary_on_call TEXT NOT NULL,
            channel TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            service TEXT NOT NULL,
            commander TEXT NOT NULL,
            status TEXT NOT NULL,
            started_min_ago INTEGER NOT NULL,
            resolved_min_ago INTEGER
        );
        CREATE TABLE IF NOT EXISTS deploys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            version TEXT NOT NULL,
            team TEXT NOT NULL,
            author TEXT NOT NULL,
            minutes_ago INTEGER NOT NULL,
            result TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY,
            service TEXT NOT NULL,
            action TEXT NOT NULL,
            from_version TEXT NOT NULL,
            to_version TEXT NOT NULL,
            reason TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            status TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            consumed INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    if cur.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        service_rows = []
        for (name, team, tier, slo, p95_target, base_rpm, _, _, _, replicas, version, prev, consumed) in SERVICES:
            requests_30d = int(base_rpm * 0.62 * 60 * 24 * 30)
            errors_30d = int(requests_30d * (100 - slo) / 100 * consumed)
            service_rows.append((name, team, tier, slo, p95_target, replicas, version, prev, requests_30d, errors_30d))
        cur.executemany("INSERT INTO services VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", service_rows)
        cur.executemany("INSERT INTO on_call VALUES (?, ?, ?, ?)", ON_CALL)
        cur.executemany("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", INCIDENTS)
        cur.executemany(
            "INSERT INTO deploys (service, version, team, author, minutes_ago, result) VALUES (?, ?, ?, ?, ?, ?)",
            DEPLOYS,
        )

    anchor = _now_bucket()
    row = cur.execute("SELECT value FROM meta WHERE key = 'telemetry_anchor'").fetchone()
    stale = row is None or anchor - datetime.fromisoformat(row["value"]) > timedelta(hours=REGENERATE_AFTER_HOURS)
    if stale:
        cur.execute("DELETE FROM metrics")
        cur.executemany("INSERT INTO metrics VALUES (?, ?, ?, ?, ?, ?)", _generate_metrics(anchor))
        cur.execute("INSERT OR REPLACE INTO meta VALUES ('telemetry_anchor', ?)", (anchor.isoformat(),))

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def fetch_services() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT s.*, o.primary_on_call, o.secondary_on_call, o.channel
            FROM services s JOIN on_call o ON o.team = s.team
            ORDER BY s.tier, s.service
            """
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_service(service: str) -> dict[str, Any] | None:
    return next((s for s in fetch_services() if s["service"] == service), None)


def service_snapshot() -> list[dict[str, Any]]:
    """One row per service with SLO maths, the latest telemetry and 24 hourly p95 points."""
    services = fetch_services()
    with connect() as conn:
        latest = {
            r["service"]: dict(r)
            for r in conn.execute(
                "SELECT service, requests, errors, p50_ms, p95_ms FROM metrics WHERE bucket = ?",
                (BUCKETS - 1,),
            )
        }
        hourly: dict[str, list[float]] = {}
        for r in conn.execute(
            """
            SELECT service, bucket / 12 AS hour, MAX(p95_ms) AS p95_ms
            FROM metrics GROUP BY service, hour ORDER BY service, hour
            """
        ):
            hourly.setdefault(r["service"], []).append(round(r["p95_ms"], 1))
        last_deploy = {
            r["service"]: dict(r)
            for r in conn.execute(
                """
                SELECT service, version, minutes_ago, result FROM deploys d
                WHERE minutes_ago = (SELECT MIN(minutes_ago) FROM deploys WHERE service = d.service)
                """
            )
        }
        open_incidents = {
            r["service"]: dict(r)
            for r in conn.execute(
                "SELECT service, incident_id, severity FROM incidents WHERE status != 'Resolved'"
            )
        }

    snapshot = []
    for s in services:
        m = latest[s["service"]]
        availability = 100 * (1 - s["errors_30d"] / s["requests_30d"])
        allowed_errors = s["requests_30d"] * (100 - s["slo_availability_pct"]) / 100
        budget_remaining = 100 * (1 - s["errors_30d"] / allowed_errors)
        deploy = last_deploy.get(s["service"])
        incident = open_incidents.get(s["service"])
        snapshot.append(
            {
                "service": s["service"],
                "team": s["team"],
                "tier": s["tier"],
                "on_call": s["primary_on_call"],
                "slo_availability_pct": s["slo_availability_pct"],
                "availability_30d_pct": round(availability, 3),
                "requests_30d": s["requests_30d"],
                "errors_30d": s["errors_30d"],
                "error_budget_remaining_pct": round(budget_remaining, 1),
                "requests_per_min": round(m["requests"] / BUCKET_MINUTES),
                "error_rate_pct": round(100 * m["errors"] / max(1, m["requests"]), 2),
                "p50_ms": m["p50_ms"],
                "p95_ms": m["p95_ms"],
                "p95_target_ms": s["p95_target_ms"],
                "p95_24h": hourly.get(s["service"], []),
                "replicas": s["replicas"],
                "version": s["version"],
                "last_deploy": (
                    {
                        "version": deploy["version"],
                        "at": minutes_ago_to_iso(deploy["minutes_ago"]),
                        "result": deploy["result"],
                    }
                    if deploy
                    else None
                ),
                "open_incident": incident,
                "status": _service_status(budget_remaining, m["p95_ms"], s["p95_target_ms"], incident),
            }
        )
    return snapshot


def _service_status(budget: float, p95: float, target: float, incident: dict | None) -> str:
    if budget < 0 or (incident and incident["severity"] in ("SEV1", "SEV2")):
        return "critical"
    if incident or p95 > target:
        return "degraded"
    if budget < 25:
        return "at_risk"
    return "healthy"


def fetch_timeseries(service: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT bucket, requests, errors, p50_ms, p95_ms FROM metrics WHERE service = ? ORDER BY bucket",
            (service,),
        ).fetchall()
    return [
        {
            "t": bucket_to_iso(r["bucket"]),
            "requests_per_min": round(r["requests"] / BUCKET_MINUTES),
            "error_rate_pct": round(100 * r["errors"] / max(1, r["requests"]), 3),
            "p50_ms": r["p50_ms"],
            "p95_ms": r["p95_ms"],
        }
        for r in rows
    ]


def fleet_hourly() -> list[dict[str, Any]]:
    """Fleet-wide requests/min and error rate per hour for the last 24 hours."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT bucket / 12 AS hour, SUM(requests) AS requests, SUM(errors) AS errors
            FROM metrics GROUP BY hour ORDER BY hour
            """
        ).fetchall()
    return [
        {
            "requests_per_min": round(r["requests"] / (12 * BUCKET_MINUTES)),
            "error_rate_pct": round(100 * r["errors"] / max(1, r["requests"]), 3),
        }
        for r in rows
    ]


def fetch_incidents(status: str = "all", service: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM incidents WHERE 1 = 1"
    params: list[Any] = []
    if status == "open":
        query += " AND status != 'Resolved'"
    elif status == "resolved":
        query += " AND status = 'Resolved'"
    if service:
        query += " AND service = ?"
        params.append(service)
    query += " ORDER BY (status = 'Resolved'), started_min_ago"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    incidents = []
    for r in rows:
        end = r["resolved_min_ago"] if r["resolved_min_ago"] is not None else 0
        incidents.append(
            {
                "incident_id": r["incident_id"],
                "severity": r["severity"],
                "title": r["title"],
                "service": r["service"],
                "commander": r["commander"],
                "status": r["status"],
                "started_at": minutes_ago_to_iso(r["started_min_ago"]),
                "resolved_at": (
                    minutes_ago_to_iso(r["resolved_min_ago"]) if r["resolved_min_ago"] is not None else None
                ),
                "duration_min": r["started_min_ago"] - end,
            }
        )
    return incidents


def fetch_deploys(limit: int = 20, service: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM deploys"
    params: list[Any] = []
    if service:
        query += " WHERE service = ?"
        params.append(service)
    query += " ORDER BY minutes_ago LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "service": r["service"],
            "version": r["version"],
            "team": r["team"],
            "author": r["author"],
            "at": minutes_ago_to_iso(r["minutes_ago"]),
            "minutes_ago": r["minutes_ago"],
            "result": r["result"],
        }
        for r in rows
    ]


def fetch_approvals(status: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM approvals"
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY requested_at DESC"
    with connect() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def fetch_approval(approval_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    return dict(row) if row else None


def create_approval(service: str, action: str, from_version: str, to_version: str, reason: str, requested_by: str) -> dict[str, Any]:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
        approval_id = f"APR-{1041 + count}"
        conn.execute(
            """
            INSERT INTO approvals (approval_id, service, action, from_version, to_version, reason,
                                   requested_by, requested_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
            """,
            (approval_id, service, action, from_version, to_version, reason, requested_by,
             datetime.now(timezone.utc).isoformat()),
        )
    return fetch_approval(approval_id)


def decide_approval(approval_id: str, approve: bool, decided_by: str) -> dict[str, Any] | None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?
            WHERE approval_id = ? AND status = 'PENDING'
            """,
            ("APPROVED" if approve else "REJECTED", decided_by, datetime.now(timezone.utc).isoformat(), approval_id),
        )
    return fetch_approval(approval_id)


def record_change(service: str, action: str, detail: str, actor: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO change_log (service, action, detail, actor, created_at) VALUES (?, ?, ?, ?, ?)",
            (service, action, detail, actor, datetime.now(timezone.utc).isoformat()),
        )


def fetch_change_log(limit: int = 20) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM change_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def set_replicas(service: str, replicas: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE services SET replicas = ? WHERE service = ?", (replicas, service))


def roll_back(service: str, actor: str) -> dict[str, Any]:
    """Moves a service back to its previous version and records the rollback as a deploy."""
    svc = fetch_service(service)
    with connect() as conn:
        conn.execute(
            "UPDATE services SET version = previous_version, previous_version = ? WHERE service = ?",
            (svc["version"], service),
        )
        conn.execute(
            "INSERT INTO deploys (service, version, team, author, minutes_ago, result) VALUES (?, ?, ?, ?, 0, 'rollback')",
            (service, svc["previous_version"], svc["team"], actor),
        )
        conn.execute(
            "UPDATE incidents SET status = 'Monitoring' WHERE service = ? AND status != 'Resolved'",
            (service,),
        )
    return {"from_version": svc["version"], "to_version": svc["previous_version"]}
