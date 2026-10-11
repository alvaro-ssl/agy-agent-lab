"""Function tools that let an ADK agent analyse the company digital twin and act on it.

Analyse:  get_company_overview, list_twin_tables, query_twin (read-only SQL), get_kpi_trend, get_signals
Decide:   simulate_decision (what-if), get_decision_rights
Act:      take_action — autonomous within decision rights, otherwise files an approval for a human

The twin lives in company-twin/data/twin.db (run generate_twin.py first). Human approvals are given in the
Decision Inbox (inbox_app.py, http://localhost:8090).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "data" / "twin.db"
RIGHTS_PATH = HERE / "decision_rights.yaml"
AGENT_ACTOR = "twin-agent"
MAX_ROWS = 200

LAYERS = {
    "1 strategy & objectives": ["company", "business_units", "objectives", "leadership", "regions"],
    "2 organisation & people": ["org_units"],
    "3 customers & market": ["customer_segments"],
    "4 products & services": ["product_lines"],
    "5 operations & processes": ["processes"],
    "6 supply chain & assets": ["suppliers", "sites"],
    "7 finance": ["monthly_financials"],
    "8 risk & governance": ["risks", "policies"],
    "signals & history": ["signals", "monthly_kpis"],
    "decisions": ["approvals", "actions_log"],
}


def _connect(read_only: bool = True) -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError("The twin has not been generated yet: run `python company-twin/generate_twin.py`.")
    uri = f"file:{DB_PATH}?mode=ro" if read_only else f"file:{DB_PATH}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _leaders() -> dict[str, str]:
    return {r["role"]: r["name"] for r in _rows("SELECT role, name FROM leadership")}


def _find(table: str, id_col: str, target: str) -> dict[str, Any] | None:
    """Look an entity up by id or (case-insensitive, partial) name."""
    t = (target or "").strip().lower()
    rows = _rows(f"SELECT * FROM {table}")
    return (next((r for r in rows if str(r[id_col]).lower() == t), None)
            or next((r for r in rows if str(r.get("name", "")).lower() == t), None)
            or next((r for r in rows if t and t in str(r.get("name", "")).lower()), None))


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

def get_company_overview() -> dict[str, Any]:
    """Returns the company profile, leadership, business units vs targets, objectives and open signals.

    Start here: it summarises every layer of the digital twin and names the tables to query for detail.
    """
    company = _rows("SELECT * FROM company")[0]
    months = [r["month"] for r in _rows("SELECT DISTINCT month FROM monthly_financials ORDER BY month")]
    last12, prev12 = months[-12:], months[-24:-12]
    bus = []
    for bu in _rows("SELECT * FROM business_units"):
        fin = _rows("SELECT * FROM monthly_financials WHERE bu_id = ?", (bu["bu_id"],))
        rev = sum(r["revenue"] for r in fin if r["month"] in last12)
        prev = sum(r["revenue"] for r in fin if r["month"] in prev12)
        ebitda = sum(r["ebitda"] for r in fin if r["month"] in last12)
        budget = sum(r["budget_revenue"] for r in fin if r["month"] in last12)
        bus.append({"bu_id": bu["bu_id"], "name": bu["name"], "head": bu["head"],
                    "revenue_last_12m": round(rev), "growth_pct": round(100 * (rev / prev - 1), 1),
                    "growth_target_pct": bu["growth_target_pct"], "vs_budget_pct": round(100 * (rev / budget - 1), 1),
                    "ebitda_margin_pct": round(100 * ebitda / rev, 1)})
    return {
        "company": company,
        "leadership": _leaders(),
        "business_units": bus,
        "objectives": _rows("SELECT * FROM objectives WHERE target IS NOT NULL"),
        "strategic_priorities": [r["objective"] for r in _rows("SELECT objective FROM objectives WHERE target IS NULL")],
        "open_signals": _rows("SELECT signal_id, severity, layer, title FROM signals ORDER BY severity, detected_days_ago"),
        "layers": LAYERS,
    }


def list_twin_tables() -> dict[str, Any]:
    """Lists every table in the digital twin with its layer, columns and row count, for writing query_twin SQL."""
    out = {}
    with _connect() as conn:
        for layer, tables in LAYERS.items():
            for t in tables:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
                count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                out[t] = {"layer": layer, "columns": cols, "rows": count}
    out["_notes"] = ("monthly_kpis is long format: (month, entity_type, entity_id, entity_name, metric, value). "
                     "entity_type is one of segment, product_line, process, org_unit, supplier, company.")
    return out


def query_twin(sql: str) -> dict[str, Any]:
    """Runs a read-only SQL SELECT against the digital twin (SQLite) and returns up to 200 rows.

    Args:
        sql: A single SELECT statement, e.g. "SELECT name, churn_monthly_pct, nps FROM customer_segments".
    """
    statement = sql.strip().rstrip(";")
    if not statement.lower().startswith(("select", "with")) or ";" in statement:
        return {"status": "ERROR", "message": "Only a single read-only SELECT statement is allowed."}
    try:
        with _connect(read_only=True) as conn:
            cur = conn.execute(statement)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS + 1)
    except sqlite3.Error as exc:
        return {"status": "ERROR", "message": str(exc)}
    return {"columns": cols, "rows": [list(r) for r in rows[:MAX_ROWS]], "truncated": len(rows) > MAX_ROWS}


def get_kpi_trend(entity_type: str, entity: str, metric: str, months: int = 12) -> dict[str, Any]:
    """Returns the monthly trend of one KPI for one entity.

    Args:
        entity_type: segment, product_line, process, org_unit, supplier or company.
        entity: The entity's id or name (e.g. 'SEG2' or 'Online subscribers'); 'GROUP' for company.
        metric: e.g. churn_monthly_pct, nps, gross_margin_pct, unit_cost, cycle_time_hours, backlog,
            sla_attainment_pct, attrition_annualised_pct, engagement_score, lead_time_days, on_time_delivery_pct,
            revenue, dso_days, cash.
        months: How many recent months to return (default 12).
    """
    rows = _rows(
        "SELECT month, entity_id, entity_name, value FROM monthly_kpis WHERE entity_type = ? AND metric = ? "
        "AND (lower(entity_id) = lower(?) OR lower(entity_name) = lower(?)) ORDER BY month",
        (entity_type, metric, entity, entity),
    )
    if not rows:
        metrics = sorted({r["metric"] for r in _rows("SELECT DISTINCT metric FROM monthly_kpis WHERE entity_type = ?", (entity_type,))})
        return {"status": "ERROR", "message": f"No data for {entity_type} '{entity}' / {metric}. Metrics for {entity_type}: {metrics}"}
    rows = rows[-months:]
    first, last = rows[0]["value"], rows[-1]["value"]
    return {"entity": rows[0]["entity_name"], "metric": metric,
            "series": [{"month": r["month"], "value": round(r["value"], 2)} for r in rows],
            "change_pct": round(100 * (last / first - 1), 1) if first else None}


def get_signals() -> list[dict[str, Any]]:
    """Returns the anomalies detected in the twin, with severity, evidence and which signal caused which."""
    return _rows("SELECT * FROM signals ORDER BY detected_days_ago")


# ---------------------------------------------------------------------------
# Decide
# ---------------------------------------------------------------------------

def _rights() -> dict[str, Any]:
    return yaml.safe_load(RIGHTS_PATH.read_text())


def evaluate_decision_rights(action_type: str, amount: float = 0.0) -> dict[str, Any]:
    """What decision_rights.yaml says about one action: AUTONOMOUS, NEEDS_APPROVAL (and by whom) or FORBIDDEN."""
    rights = _rights()
    rule = rights.get("actions", {}).get(action_type) or {**rights.get("default", {"mode": "approval", "approver": "CEO"}),
                                                          "description": "Not in the decision rights — default rule."}
    mode = rule.get("mode", "approval")
    leaders = _leaders()
    approver = rule.get("approver")
    result = {"action_type": action_type, "rule": rule, "unit": rule.get("unit", "none")}
    if mode == "forbidden":
        return {**result, "decision": "FORBIDDEN"}
    if mode == "autonomous" or (mode == "threshold" and abs(float(amount or 0)) <= float(rule.get("autonomous_up_to", 0))):
        return {**result, "decision": "AUTONOMOUS"}
    return {**result, "decision": "NEEDS_APPROVAL", "approver_role": approver, "approver_name": leaders.get(approver, approver)}


def get_decision_rights() -> dict[str, Any]:
    """Returns the agent's decision rights: which actions it may take alone, up to what limit, which need which
    executive's approval, and which are forbidden. Executive names are resolved from the twin's leadership."""
    rights = _rights()
    leaders = _leaders()
    for rule in [rights.get("default", {}), *rights.get("actions", {}).values()]:
        if rule.get("approver"):
            rule["approver_name"] = leaders.get(rule["approver"], rule["approver"])
    return rights


def simulate_decision(action_type: str, target: str, amount: float) -> dict[str, Any]:
    """Estimates the business impact of a decision before taking it (a simple, transparent what-if model).

    Args:
        action_type: price_change, retention_offer, supplier_expedite, supplier_switch, hiring_requisition or
            budget_reallocation.
        target: The product line, segment, supplier, org unit or business unit concerned (id or name).
        amount: % change for price_change, number of roles for hiring_requisition, otherwise an amount of money.
    """
    company = _rows("SELECT * FROM company")[0]
    from archetypes import ARCHETYPES

    archetype = ARCHETYPES.get(company["industry"], {})
    if action_type == "price_change":
        pl = _find("product_lines", "product_line_id", target)
        if not pl:
            return {"status": "ERROR", "message": f"Unknown product line '{target}'."}
        e = archetype.get("price_elasticity", -1.0)
        pct = float(amount) / 100
        cost = get_kpi_trend("product_line", pl["product_line_id"], "unit_cost", 1)["series"][-1]["value"]
        price = pl["list_price"]
        gm_now = 1 - cost / price
        gm_new = 1 - cost / (price * (1 + pct))
        volume = 1 + e * pct
        rev_new = pl["annual_revenue"] * (1 + pct) * volume
        gp_delta = rev_new * gm_new - pl["annual_revenue"] * gm_now
        return {"action_type": action_type, "target": pl["name"], "price_change_pct": amount,
                "volume_change_pct": round(100 * (volume - 1), 1),
                "annual_revenue_change": round(rev_new - pl["annual_revenue"]),
                "gross_margin_pct": {"now": round(100 * gm_now, 1), "after": round(100 * gm_new, 1)},
                "annual_gross_profit_change": round(gp_delta),
                "assumptions": f"Price elasticity {e} for {archetype.get('label', 'this industry')}; unit cost held at today's level."}
    if action_type == "retention_offer":
        seg = _find("customer_segments", "segment_id", target)
        if not seg:
            return {"status": "ERROR", "message": f"Unknown segment '{target}'."}
        trend = get_kpi_trend("segment", seg["segment_id"], "churn_monthly_pct", 12)["series"]
        excess = max(0.0, trend[-1]["value"] - trend[0]["value"]) / 100
        at_risk = seg["customers"] * excess * 3
        retained = min(at_risk * 0.6, float(amount) / (0.08 * seg["arpu"]))
        return {"action_type": action_type, "target": seg["name"], "budget": amount,
                "customers_at_risk_next_3_months": int(at_risk), "customers_retained": int(retained),
                "annual_revenue_protected": round(retained * seg["arpu"]),
                "roi": round(retained * seg["arpu"] / float(amount), 1) if amount else None,
                "assumptions": "An offer costs ~8% of a customer's annual value; it can save up to 60% of the excess churn "
                               "over 3 months. It does not fix the underlying cause."}
    if action_type in ("supplier_expedite", "supplier_switch"):
        sup = _find("suppliers", "supplier_id", target)
        if not sup:
            return {"status": "ERROR", "message": f"Unknown supplier '{target}'."}
        if action_type == "supplier_switch":
            return {"action_type": action_type, "target": sup["name"],
                    "transition_weeks": "8-12", "annual_cost_change": round(sup["annual_spend"] * 0.05),
                    "dependency_after_pct": round(sup["dependency_pct"] / 2, 1),
                    "assumptions": "Dual-sourcing halves dependency; transition costs ~5% of annual spend; benefits start after transition."}
        needed = sup["annual_spend"] * 0.005
        share = min(1.0, float(amount) / needed)
        lt_now, lt_base = sup["current_lead_time_days"], sup["baseline_lead_time_days"]
        out = {"action_type": action_type, "target": sup["name"], "budget": amount,
               "budget_for_full_recovery": round(needed),
               "lead_time_days": {"now": lt_now, "after_4_weeks": round(lt_now - (lt_now - lt_base) * share, 1)}}
        if sup.get("supports_process_id"):
            proc = _find("processes", "process_id", sup["supports_process_id"])
            out["process_impact"] = {"process": proc["name"],
                                     "cycle_time_hours_after": round(proc["current_cycle_hours"] - (proc["current_cycle_hours"] - proc["target_cycle_hours"]) * share, 1)}
            linked = _rows("SELECT * FROM signals WHERE caused_by = 'SIG2'")
            if linked:
                seg = _find("customer_segments", "segment_id", linked[0]["entity_id"])
                trend = get_kpi_trend("segment", seg["segment_id"], "churn_monthly_pct", 12)["series"]
                excess = max(0.0, trend[-1]["value"] - trend[0]["value"]) / 100
                out["customer_impact"] = {"segment": seg["name"], "excess_churn_pct_per_month": round(100 * excess, 2),
                                          "revenue_protected_next_6_months": round(seg["annual_revenue"] / 12 * excess * 6 * 0.5 * share)}
        out["assumptions"] = ("Expediting at ~0.5% of annual spend restores the baseline lead time within ~4 weeks; less money "
                              "recovers proportionally. Once delivery recovers, half the excess churn stops within 6 months.")
        return out
    if action_type == "hiring_requisition":
        ou = _find("org_units", "org_unit_id", target)
        if not ou:
            return {"status": "ERROR", "message": f"Unknown org unit '{target}'."}
        return {"action_type": action_type, "target": ou["name"], "roles": amount,
                "annual_cost": round(float(amount) * ou["cost_per_fte"] * 1.25), "weeks_to_productive": 14,
                "open_roles_after": ou["open_roles"] + int(amount),
                "assumptions": "Fully loaded cost = 1.25 × cost per FTE; ~10 weeks to hire plus ~4 to ramp up."}
    if action_type == "budget_reallocation":
        return {"action_type": action_type, "target": target, "amount": amount,
                "assumptions": "Budget moves change where money is spent, not the group total; check the receiving unit can spend it this quarter."}
    return {"status": "ERROR", "message": f"No simulation for '{action_type}'."}


# ---------------------------------------------------------------------------
# Act
# ---------------------------------------------------------------------------

def _execute(conn: sqlite3.Connection, action_type: str, target: str, amount: float, unit: str, rationale: str,
             mode: str, authorised_by: str, approval_id: str | None) -> dict[str, Any]:
    action_id = f"ACT-{uuid.uuid4().hex[:6].upper()}"
    conn.execute("INSERT INTO actions_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (action_id, action_type, target, amount, unit, rationale, mode, authorised_by, approval_id,
                  datetime.now(timezone.utc).isoformat()))
    return {"status": "EXECUTED", "action_id": action_id, "action_type": action_type, "target": target,
            "amount": amount, "unit": unit, "mode": mode, "authorised_by": authorised_by, "approval_id": approval_id}


def take_action(action_type: str, target: str, amount: float, rationale: str, approved_by: str = "") -> dict[str, Any]:
    """Takes a business decision, within the agent's decision rights.

    - Autonomous actions (or amounts within the autonomous limit) are executed immediately and logged.
    - Actions that need a human file an approval request in the Decision Inbox and return PENDING_APPROVAL.
      Once the executive has approved, call again with approved_by set to their name.
    - Forbidden actions are refused.

    Args:
        action_type: e.g. executive_alert, create_initiative, retention_offer, price_change, budget_reallocation,
            supplier_expedite, supplier_switch, hiring_requisition (see get_decision_rights).
        target: What the action applies to (a product line, segment, supplier, org unit, business unit or executive).
        amount: Money for currency actions, % for price_change, number of roles for hiring_requisition, 0 otherwise.
        rationale: The evidence and expected impact — recorded in the audit log.
        approved_by: Name of the executive who approved the action.
    """
    verdict = evaluate_decision_rights(action_type, amount)
    unit = verdict["unit"]
    if verdict["decision"] == "FORBIDDEN":
        return {"status": "BLOCKED", "action_type": action_type, "target": target,
                "message": f"'{action_type}' is forbidden by the decision rights. Escalate to a human instead."}
    with _connect(read_only=False) as conn:
        if verdict["decision"] == "AUTONOMOUS":
            return {**_execute(conn, action_type, target, amount, unit, rationale, "autonomous", AGENT_ACTOR, None),
                    "requires_approval": False}
        if approved_by.strip():
            return {**_execute(conn, action_type, target, amount, unit, rationale, "approved", approved_by.strip(), None),
                    "requires_approval": True}
        approval_id = f"APR-{1000 + conn.execute('SELECT COUNT(*) FROM approvals').fetchone()[0] + 1}"
        conn.execute(
            "INSERT INTO approvals (approval_id, action_type, target, amount, unit, rationale, approver_role, approver_name, "
            "requested_by, requested_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')",
            (approval_id, action_type, target, amount, unit, rationale, verdict["approver_role"], verdict["approver_name"],
             AGENT_ACTOR, datetime.now(timezone.utc).isoformat()),
        )
    return {"status": "PENDING_APPROVAL", "approval_id": approval_id, "action_type": action_type, "target": target,
            "amount": amount, "unit": unit, "requires_approval": True,
            "approver": f"{verdict['approver_name']} ({verdict['approver_role']})",
            "message": f"Needs approval from {verdict['approver_name']} ({verdict['approver_role']}). "
                       f"Request {approval_id} is waiting in the Decision Inbox (http://localhost:8090). Nothing has been executed."}
