"""Database and seed data for Cymbal EMEA Operations Control Tower."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "cymbal_ops.db"

SEED_INCIDENTS = [
    (
        "INC-401",
        "NordicHome Omnichannel",
        "Retail & E-Commerce",
        "Platinum",
        "Checkout & Inventory Sync Timeout across DE/SE stores",
        "P0_CRITICAL",
        145,
        1200.0,
        "USD",
        "anna.lindqvist@nordichome.se",
        "SE45 5000 0000 0583 9825 7466",
        "OPEN",
    ),
    (
        "INC-402",
        "NeoBank26 Europe",
        "FinTech & FSI",
        "Platinum",
        "SEPA Instant Payment Webhook Latency Spike",
        "P0_CRITICAL",
        65,
        2500.0,
        "GBP",
        "m.kuveljic@neobank26.de",
        "DE89 3704 0044 0532 0130 00",
        "OPEN",
    ),
    (
        "INC-403",
        "EuroGrid & Telco",
        "Telco & Energy",
        "Gold",
        "5G Enterprise Slice Telemetry Drop — Frankfurt Core",
        "P1_HIGH",
        90,
        450.0,
        "EUR",
        "c.bannon@eurogrid.co.uk",
        "GB29 NWBK 6016 1331 9268 19",
        "OPEN",
    ),
    (
        "INC-404",
        "LuxFashion Marketplace",
        "Retail & E-Commerce",
        "Silver",
        "Delayed Return Label Generation (Iberia Region)",
        "P2_MEDIUM",
        40,
        75.0,
        "EUR",
        "l.carvalho@luxfashion.pt",
        "PT50 0002 0123 1234 5678 9015 4",
        "OPEN",
    ),
]


def init_db() -> None:
    """Initializes the local SQLite database with realistic EMEA incident data."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            vertical TEXT NOT NULL,
            sla_tier TEXT NOT NULL,
            summary TEXT NOT NULL,
            severity TEXT NOT NULL,
            downtime_mins INTEGER NOT NULL,
            penalty_rate_per_hr REAL NOT NULL,
            billing_currency TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            customer_iban TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            amount_eur REAL NOT NULL,
            manager_approved INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("SELECT COUNT(*) FROM incidents")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            """
            INSERT INTO incidents (
                incident_id, account_name, vertical, sla_tier, summary,
                severity, downtime_mins, penalty_rate_per_hr, billing_currency,
                contact_email, customer_iban, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            SEED_INCIDENTS,
        )
    from dto_digital_twin import init_dto_tables
    init_dto_tables(conn)
    conn.commit()
    conn.close()


def fetch_all_incidents() -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents ORDER BY incident_id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetch_incident_by_id(incident_id: str) -> dict[str, Any] | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def record_credit(
    incident_id: str,
    account_name: str,
    amount_eur: float,
    manager_approved: bool,
    reason: str,
) -> dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO credit_ledger (incident_id, account_name, amount_eur, manager_approved, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (incident_id, account_name, amount_eur, 1 if manager_approved else 0, reason),
    )
    cur.execute(
        "UPDATE incidents SET status = 'CREDITED' WHERE incident_id = ?",
        (incident_id,),
    )
    conn.commit()
    conn.close()
    return {
        "incident_id": incident_id,
        "account_name": account_name,
        "amount_eur": amount_eur,
        "manager_approved": manager_approved,
        "status": "CREDITED",
    }
