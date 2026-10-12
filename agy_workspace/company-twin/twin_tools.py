"""Function tools that let an ADK agent analyse the company digital twin and act on it.

Shared       get_company_overview, list_twin_tables, query_twin (read-only SQL), get_kpi_trend, get_signals,
             get_fx_rates, simulate_decision, get_decision_rights, take_action, save_report
Resilience   get_dependency_map, get_buffers, list_playbooks, simulate_shock
Margin       get_sla_exposure, evaluate_remediation_options, get_working_capital
Customer     get_at_risk_accounts, get_work_queue, research_market
Growth       get_capacity_headroom, get_market_landscape, research_market

AGENT_TYPES at the bottom maps each of the four agent designs to its toolset. The twin lives in
company-twin/data/twin.db (run generate_twin.py first). Human approvals are given in the Decision Inbox
(inbox_app.py, http://localhost:8090).
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
    "1 strategy & objectives": ["company", "business_units", "objectives", "leadership", "regions", "market_landscape"],
    "2 organisation & people": ["org_units"],
    "3 customers & market": ["customer_segments", "accounts", "friction_points"],
    "4 products & services": ["product_lines"],
    "5 operations & processes": ["processes", "work_queue", "incidents", "systems"],
    "6 supply chain & assets": ["suppliers", "sites", "dependencies"],
    "7 finance": ["monthly_financials", "fx_rates", "cost_rates"],
    "8 risk & governance": ["risks", "policies", "buffers", "mitigation_playbooks"],
    "signals & history": ["signals", "monthly_kpis"],
    "decisions": ["approvals", "actions_log", "reports"],
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
                     "entity_type is one of segment, product_line, process, org_unit, supplier, system, company. "
                     "Money columns ending in _base are in the company's currency; others are in the row's currency "
                     "(convert with fx_rates: amount / units_per_base).")
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
        action_type: price_change, retention_offer, supplier_expedite, activate_backup_supplier or budget_reallocation.
        target: The product line, segment, supplier or business unit concerned (id or name).
        amount: % change for price_change, otherwise an amount of money.
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
    if action_type in ("supplier_expedite", "supplier_switch", "activate_backup_supplier"):
        sup = _find("suppliers", "supplier_id", target)
        if not sup:
            return {"status": "ERROR", "message": f"Unknown supplier '{target}'."}
        if action_type in ("supplier_switch", "activate_backup_supplier"):
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
        action_type: one of the actions in get_decision_rights (e.g. executive_alert, prioritise_work, supplier_expedite,
            remediation_spend, customer_credit, price_change, growth_pilot).
        target: What the action applies to (a process, account, supplier, system, product line, region or executive).
        amount: Money (in the company's currency) for money actions, % for price_change, 0 otherwise.
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


# ---------------------------------------------------------------------------
# Shared helpers for the agent types
# ---------------------------------------------------------------------------

def _fx_now() -> dict[str, float]:
    last = _rows("SELECT MAX(month) AS m FROM fx_rates")[0]["m"]
    return {r["currency"]: r["units_per_base"] for r in _rows("SELECT currency, units_per_base FROM fx_rates WHERE month = ?", (last,))}


def _to_base(amount: float, currency: str, fx: dict[str, float]) -> float:
    return float(amount) / fx.get(currency, 1.0)


def _cost(name: str) -> float:
    row = _rows("SELECT value FROM cost_rates WHERE name = ?", (name,))
    return float(row[0]["value"]) if row else 0.0


def get_fx_rates() -> dict[str, Any]:
    """Returns current exchange rates (units of each currency per 1 unit of the company's currency) and the
    12-month range, for converting contract values and penalties into the company's currency."""
    base = _rows("SELECT currency FROM company")[0]["currency"]
    out = {}
    for cur in sorted({r["currency"] for r in _rows("SELECT DISTINCT currency FROM fx_rates")}):
        series = [r["units_per_base"] for r in _rows("SELECT units_per_base FROM fx_rates WHERE currency = ? ORDER BY month", (cur,))][-12:]
        out[cur] = {"now": series[-1], "min_12m": min(series), "max_12m": max(series)}
    return {"base_currency": base, "rates": out}


# ---------------------------------------------------------------------------
# Operational Resilience Agent
# ---------------------------------------------------------------------------

def get_dependency_map(target: str = "") -> dict[str, Any]:
    """Maps what depends on what. Without a target, returns the single points of failure (critical dependencies
    with no alternative). With a target (process, system, supplier, site or org unit — id or name), returns
    everything connected to it.

    Args:
        target: Optional id or name, e.g. 'P2', 'Order management system', 'S1'.
    """
    deps = _rows("SELECT * FROM dependencies")
    if target:
        t = target.lower()
        hits = [d for d in deps if t in (d["from_id"].lower(), d["to_id"].lower()) or t in d["from_name"].lower() or t in d["to_name"].lower()]
        return {"target": target, "dependencies": hits}
    spofs = [d for d in deps if d["criticality"] == "high" and not d["has_alternative"]]
    return {"single_points_of_failure": spofs,
            "systems_without_failover": _rows("SELECT * FROM systems WHERE single_point_of_failure = 1"),
            "dependency_count": len(deps)}


def get_buffers() -> list[dict[str, Any]]:
    """Returns operational and regulatory buffers (capacity headroom, days of cover, SLA attainment, regulatory
    ratios) with their thresholds and the projected days until each is breached at the current trend."""
    return _rows("SELECT * FROM buffers ORDER BY CASE WHEN days_to_breach IS NULL THEN 9999 ELSE days_to_breach END")


def list_playbooks(target: str = "") -> list[dict[str, Any]]:
    """Lists the mitigation playbooks (pre-agreed responses) with cost, time to effect, how much of the current
    disruption they remove, and the take_action type that executes them.

    Args:
        target: Optional filter — a signal id (e.g. 'SIG2'), or a target id or name.
    """
    rows = _rows("SELECT * FROM mitigation_playbooks")
    if not target:
        return rows
    t = target.lower()
    return [r for r in rows if t in r["addresses"].lower() or t in r["target_id"].lower() or t in r["target_name"].lower() or t in r["name"].lower()]


def simulate_shock(shock_type: str, target: str, severity_pct: float = 50.0, duration_days: float = 7.0) -> dict[str, Any]:
    """Runs a causal "what-if" shock through the twin and returns the blast radius: affected processes, key
    accounts, revenue at risk, SLA penalties, buffers and regulatory thresholds breached, and which playbooks
    would cost less than the disruption.

    Args:
        shock_type: supplier_delay, system_brownout, site_outage or staffing_shortage.
        target: The supplier, system, site or org unit hit (id or name).
        severity_pct: How hard it is hit (0-100), e.g. 50 = half its capacity lost.
        duration_days: How long the shock lasts.
    """
    deps = _rows("SELECT * FROM dependencies")
    t = target.strip().lower()
    hit = [d for d in deps if d["to_id"].lower() == t or t in d["to_name"].lower()]
    if not hit:
        return {"status": "ERROR", "message": f"Nothing in the twin depends on '{target}'. Try get_dependency_map()."}
    sev = min(100.0, max(0.0, float(severity_pct))) / 100
    fx = _fx_now()
    processes = {p["process_id"]: p for p in _rows("SELECT * FROM processes")}
    bus = {b["bu_id"]: b for b in _rows("SELECT * FROM business_units")}
    rev = _rows("SELECT annual_revenue FROM company")[0]["annual_revenue"]
    impacts, revenue_day, penalties_day, accounts = [], 0.0, 0.0, {}
    for d in hit:
        weight = (1.0 if d["criticality"] == "high" else 0.5) * (0.4 if d["has_alternative"] else 1.0)
        impact = sev * weight
        proc = processes.get(d["from_id"])
        if not proc:
            continue
        customer_facing = proc["process_id"] in ("P2", "P3")
        bu_rev = rev * bus[proc["owner_bu_id"]]["revenue_share"]
        r_day = bu_rev / 365 * impact * (0.3 if customer_facing else 0.1)
        revenue_day += r_day
        for w in _rows("SELECT w.*, a.name, a.sla_penalty_per_hour, a.currency, a.tier FROM work_queue w JOIN accounts a USING (account_id) WHERE w.process_id = ?", (proc["process_id"],)):
            p_day = _to_base(w["sla_penalty_per_hour"], w["currency"], fx) * 24 * impact * (1.0 if w["items_breaching_sla"] else 0.5)
            penalties_day += p_day
            accounts[w["account_id"]] = {"account": w["name"], "tier": w["tier"], "penalties_per_day": round(p_day)}
        impacts.append({"process": proc["name"], "dependency": d["criticality"], "has_alternative": bool(d["has_alternative"]),
                        "capacity_lost_pct": round(100 * impact, 1),
                        "cycle_time_hours_after": round(proc["current_cycle_hours"] * (1 + impact * 1.5), 1),
                        "sla_attainment_after_pct": round(max(40.0, proc["current_sla_attainment_pct"] - impact * 40), 1),
                        "revenue_at_risk_per_day": round(r_day)})
    days = float(duration_days)
    disruption_cost = (revenue_day + penalties_day) * days
    linked = {d["from_id"] for d in hit} | {d["to_id"] for d in hit}
    buffers = []
    for b in _rows("SELECT * FROM buffers"):
        if b["entity_id"] in linked or b["regulatory"]:
            after = None if b["days_to_breach"] is None else round(b["days_to_breach"] / (1 + 2 * sev), 1)
            buffers.append({"buffer": b["name"], "days_to_breach_now": b["days_to_breach"], "days_to_breach_in_shock": after,
                            "breached_during_shock": after is not None and after <= days, "regulatory": bool(b["regulatory"])})
    playbooks = []
    for pb in _rows("SELECT * FROM mitigation_playbooks"):
        if pb["target_id"] in linked or any(i["process"] == pb["target_name"] for i in impacts):
            cost = pb["one_off_cost_base"] + pb["daily_cost_base"] * days
            playbooks.append({"playbook": pb["name"], "action_type": pb["action_type"], "cost": round(cost),
                              "mitigate_now": cost < disruption_cost * pb["burn_reduction_pct"] / 100})
    return {"shock": {"type": shock_type, "target": hit[0]["to_name"], "severity_pct": severity_pct, "duration_days": days},
            "processes": impacts, "key_accounts_affected": list(accounts.values()),
            "revenue_at_risk": round(revenue_day * days), "sla_penalties": round(penalties_day * days),
            "total_disruption_cost": round(disruption_cost), "buffers": buffers, "playbooks": playbooks,
            "assumptions": "Critical dependencies transmit the full shock, medium ones half; an alternative absorbs 60%. "
                           "Customer-facing processes put 30% of the owning unit's daily revenue at risk per unit of lost capacity."}


# ---------------------------------------------------------------------------
# Margin & Cash Guardian Agent
# ---------------------------------------------------------------------------

def get_sla_exposure(account: str = "") -> dict[str, Any]:
    """Returns SLA penalty exposure per key-account contract: penalty per hour and accrued so far in the contract
    currency and in the company's currency, and hours left before each contract's penalty cap.

    Args:
        account: Optional account id or name; empty returns every contract currently in breach.
    """
    fx = _fx_now()
    rows = _rows("SELECT * FROM accounts WHERE sla_hours_in_breach > 0") if not account else [
        a for a in _rows("SELECT * FROM accounts") if account.lower() in (a["account_id"].lower(), a["name"].lower())]
    contracts, by_cur = [], {}
    for a in rows:
        hours_to_cap = (a["sla_penalty_cap"] - a["sla_penalty_accrued"]) / a["sla_penalty_per_hour"] if a["sla_penalty_per_hour"] else None
        contracts.append({"account_id": a["account_id"], "account": a["name"], "tier": a["tier"], "currency": a["currency"],
                          "penalty_per_hour": a["sla_penalty_per_hour"], "accrued": a["sla_penalty_accrued"],
                          "penalty_per_hour_base": round(_to_base(a["sla_penalty_per_hour"], a["currency"], fx), 2),
                          "accrued_base": round(_to_base(a["sla_penalty_accrued"], a["currency"], fx)),
                          "hours_until_cap": round(hours_to_cap) if hours_to_cap else None})
        cur = by_cur.setdefault(a["currency"], {"per_hour": 0.0, "accrued": 0.0})
        cur["per_hour"] += a["sla_penalty_per_hour"]
        cur["accrued"] += a["sla_penalty_accrued"]
    return {"contracts": contracts, "by_currency": {k: {kk: round(vv) for kk, vv in v.items()} for k, v in by_cur.items()},
            "total_per_hour_base": round(sum(c["penalty_per_hour_base"] for c in contracts)),
            "total_accrued_base": round(sum(c["accrued_base"] for c in contracts))}


def evaluate_remediation_options(target: str = "") -> dict[str, Any]:
    """Compares every remediation option for the current disruption on money: the hourly burn of doing nothing
    (SLA penalties, rework, revenue at risk), and for each option its cost, net present value over 90 days and
    payback. Flags a "negative-margin loop" when the disruption burns more per hour than burst capacity costs.

    Args:
        target: Optional filter — a signal id (e.g. 'SIG8'), or a playbook target id or name. Empty compares the
            options for the live supplier -> process -> customer disruption.
    """
    exposure = get_sla_exposure()
    rework_h = sum(w["items_breaching_sla"] for w in _rows("SELECT items_breaching_sla FROM work_queue")) * _cost("rework_cost_per_item") / 24
    churn_h = _cost("revenue_at_risk_per_hour_from_churn")
    burn_h = exposure["total_per_hour_base"] + rework_h + churn_h
    r = _cost("discount_rate_pct_per_year") / 100
    options = []
    disruption = {"SIG1", "SIG2", "SIG7", "SIG8"}  # the live supplier -> process -> customer disruption
    candidates = list_playbooks(target) if target else [
        pb for pb in list_playbooks() if disruption & {x.strip() for x in pb["addresses"].split(",")}]
    for pb in candidates:
        avoided_day = burn_h * 24 * pb["burn_reduction_pct"] / 100
        npv, cum, payback = -pb["one_off_cost_base"], -pb["one_off_cost_base"], None
        for d in range(1, 91):
            flow = (avoided_day if d > pb["time_to_effect_days"] else 0) - pb["daily_cost_base"]
            npv += flow / (1 + r) ** (d / 365)
            cum += flow
            if payback is None and cum >= 0 and d > pb["time_to_effect_days"]:
                payback = d
        commitment = pb["one_off_cost_base"] + pb["daily_cost_base"] * 30
        verdict = evaluate_decision_rights(pb["action_type"], commitment)
        options.append({"playbook": pb["name"], "action_type": pb["action_type"], "target": pb["target_name"],
                        "one_off_cost": round(pb["one_off_cost_base"]), "daily_cost": round(pb["daily_cost_base"]),
                        "first_month_commitment": round(commitment), "removes_burn_pct": pb["burn_reduction_pct"],
                        "starts_working_in_days": pb["time_to_effect_days"], "npv_90_days": round(npv),
                        "payback_days": payback, "decision": verdict["decision"], "approver": verdict.get("approver_name")})
    options.sort(key=lambda o: -o["npv_90_days"])
    burst = _cost("burst_capacity_per_hour")
    return {"burn_per_hour": {"sla_penalties": exposure["total_per_hour_base"], "rework": round(rework_h),
                              "revenue_at_risk_from_churn": round(churn_h), "total": round(burn_h)},
            "negative_margin_loop": burn_h > burst, "burst_capacity_cost_per_hour": burst,
            "penalties_by_currency": exposure["by_currency"], "options": options,
            "assumptions": f"90-day horizon, {r * 100:.0f}% annual discount rate; amounts in the company's currency."}


def get_working_capital() -> dict[str, Any]:
    """Returns working-capital trends (DSO, DIO, DPO, cash) for the last 12 months and the value tied up in work
    that is breaching its SLA."""
    out = {}
    for metric in ("dso_days", "dio_days", "dpo_days", "cash"):
        out[metric] = get_kpi_trend("company", "GROUP", metric, 12)["series"]
    fx = _fx_now()
    locked = sum(_to_base(w["value_at_risk"], w["currency"], fx) for w in _rows("SELECT * FROM work_queue WHERE items_breaching_sla > 0"))
    out["value_tied_up_in_breaching_work"] = round(locked)
    out["carrying_cost_pct_per_year"] = _cost("inventory_carrying_cost_pct_per_year")
    return out


# ---------------------------------------------------------------------------
# Customer Rescue Agent
# ---------------------------------------------------------------------------

def get_at_risk_accounts(within_days: int = 90) -> list[dict[str, Any]]:
    """Returns key accounts that renew within the window and are at risk (work breaching SLA or high churn risk),
    most valuable first, with tier, contract value, health, NPS, the stuck work hurting them, penalties accrued,
    goodwill-credit ceiling and the account owner. No personal data — contacts are roles only.

    Args:
        within_days: Renewal window in days (default 90).
    """
    fx = _fx_now()
    out = []
    for a in _rows("SELECT * FROM accounts WHERE renewal_in_days <= ? ORDER BY annual_contract_value_base DESC", (within_days,)):
        work = _rows("SELECT w.*, p.name AS process FROM work_queue w JOIN processes p USING (process_id) WHERE account_id = ?", (a["account_id"],))
        breaching = [w for w in work if w["items_breaching_sla"]]
        if not breaching and a["churn_risk_pct"] < 30:
            continue
        out.append({"account_id": a["account_id"], "account": a["name"], "industry": a["industry"], "region": a["region"],
                    "tier": a["tier"], "renewal_in_days": a["renewal_in_days"],
                    "annual_contract_value_base": round(a["annual_contract_value_base"]),
                    "health_score": a["health_score"], "nps": a["nps"], "churn_risk_pct": a["churn_risk_pct"],
                    "stuck_work": [{"process": w["process"], "items_breaching_sla": w["items_breaching_sla"],
                                    "oldest_item_age_hours": w["oldest_item_age_hours"], "sla_hours": w["sla_hours"]} for w in breaching],
                    "sla_penalty_accrued_base": round(_to_base(a["sla_penalty_accrued"], a["currency"], fx)),
                    "goodwill_credit_ceiling_base": round(_to_base(a["goodwill_credit_ceiling"], a["currency"], fx)),
                    "account_owner": a["account_owner"], "contact_role": a["contact_role"]})
    return sorted(out, key=lambda x: -x["annual_contract_value_base"] * x["churn_risk_pct"])


def get_work_queue(account: str = "", process: str = "") -> list[dict[str, Any]]:
    """Returns open work items per account and process — how many are breaching SLA, the oldest item's age and
    what is blocking them.

    Args:
        account: Optional account id or name.
        process: Optional process id or name.
    """
    rows = _rows("SELECT w.*, a.name AS account, a.tier, p.name AS process FROM work_queue w "
                 "JOIN accounts a USING (account_id) JOIN processes p USING (process_id)")
    if account:
        rows = [r for r in rows if account.lower() in (r["account_id"].lower(), r["account"].lower())]
    if process:
        rows = [r for r in rows if process.lower() in (r["process_id"].lower(), r["process"].lower())]
    return sorted(rows, key=lambda r: -r["items_breaching_sla"])


def research_market(query: str) -> dict[str, Any]:
    """Researches the outside world — a market, an industry, competitors, or the kind of business a customer is
    in — using Google Search grounding, falling back to Google News headlines, so internal analysis can be
    combined with public intelligence. Never use it to look up private individuals.

    Args:
        query: What to research, e.g. 'quick commerce growth Germany 2026' or 'hotel groups procurement trends'.
    """
    try:
        from google import genai
        from google.genai import types

        resp = genai.Client().models.generate_content(
            model="gemini-3.6-flash",
            contents=f"Research this with Google Search and summarise the key facts, figures and trends in 6 bullet points, citing sources: {query}",
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.2),
        )
        if resp and resp.text:
            return {"query": query, "status": "OK", "source": "google_search_grounding", "summary": resp.text.strip()[:4000]}
    except Exception:
        pass
    try:
        import urllib.parse
        import urllib.request
        import xml.etree.ElementTree as ET

        url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(query)}&hl=en-GB&gl=GB&ceid=GB:en"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=6) as r:
            items = [i.findtext("title") for i in ET.fromstring(r.read()).findall(".//item")[:8]]
        if items:
            return {"query": query, "status": "OK", "source": "google_news_headlines", "headlines": items}
    except Exception:
        pass
    return {"query": query, "status": "OFFLINE", "message": "No internet access — rely on the twin's market_landscape table."}


# ---------------------------------------------------------------------------
# Growth Scout Agent
# ---------------------------------------------------------------------------

def get_capacity_headroom() -> dict[str, Any]:
    """Returns capacity the company already pays for but does not use: under-utilised sites, teams with spare
    capacity and systems with headroom — the raw material for growth plays."""
    return {"sites": _rows("SELECT * FROM sites WHERE utilization_pct < 70 ORDER BY utilization_pct"),
            "teams": _rows("SELECT org_unit_id, name, headcount, utilization_pct FROM org_units WHERE utilization_pct < 80 ORDER BY utilization_pct"),
            "systems": _rows("SELECT system_id, name, capacity_headroom_pct FROM systems WHERE capacity_headroom_pct >= 30")}


def get_market_landscape(region: str = "", opportunity: str = "") -> dict[str, Any]:
    """Returns the market landscape for adjacent growth plays per region — market size, growth, our share, the
    leading competitor, estimated margin and our capability fit — plus customer friction points that signal
    unmet demand.

    Args:
        region: Optional region filter.
        opportunity: Optional opportunity filter.
    """
    rows = _rows("SELECT * FROM market_landscape")
    if region:
        rows = [r for r in rows if region.lower() in r["region"].lower()]
    if opportunity:
        rows = [r for r in rows if opportunity.lower() in r["opportunity"].lower()]
    rows.sort(key=lambda r: -(r["market_size_base"] * r["growth_pct_per_year"]))
    return {"market": rows, "friction_points": _rows("SELECT * FROM friction_points ORDER BY trend_pct DESC")}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def save_report(title: str, content: str) -> dict[str, Any]:
    """Saves a markdown report (briefing, memo, business case) so executives can read it in the Decision Inbox.

    Args:
        title: The report title.
        content: The full report in markdown.
    """
    import re

    reports = HERE / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "report"
    path = reports / f"{stamp:%Y%m%d-%H%M%S}-{slug}.md"
    path.write_text(f"# {title}\n\n{content}\n")
    report_id = f"RPT-{stamp:%H%M%S}"
    with _connect(read_only=False) as conn:
        conn.execute("INSERT INTO reports VALUES (?, ?, ?, ?, ?)", (report_id, title, str(path.relative_to(HERE)), stamp.isoformat(), AGENT_ACTOR))
    return {"status": "SAVED", "report_id": report_id, "path": str(path), "view": "http://localhost:8090"}


# ---------------------------------------------------------------------------
# The four agent designs
# ---------------------------------------------------------------------------

_SHARED = ["get_company_overview", "list_twin_tables", "query_twin", "get_kpi_trend", "get_signals",
           "get_decision_rights", "take_action", "save_report"]

AGENT_TYPES: dict[str, dict[str, Any]] = {
    "operational_resilience": {
        "name": "Operational Resilience Agent", "sponsor": "COO / CRO",
        "mission": "Move from firefighting to prevention: stress-test operations against internal bottlenecks and "
                   "external shocks, find single points of failure, and act before disruptions cascade.",
        "tools": _SHARED + ["get_dependency_map", "get_buffers", "list_playbooks", "simulate_shock"],
        "actions": ["executive_alert", "create_initiative", "throttle_noncritical", "reroute_capacity",
                    "supplier_expedite", "activate_backup_supplier", "system_capacity_increase"],
    },
    "margin_guardian": {
        "name": "Margin & Cash Guardian Agent", "sponsor": "CFO",
        "mission": "Protect operating margin and working capital in real time by translating operational telemetry "
                   "into P&L impact and stopping negative-margin loops.",
        "tools": _SHARED + ["get_fx_rates", "get_sla_exposure", "evaluate_remediation_options", "get_working_capital", "simulate_decision"],
        "actions": ["executive_alert", "create_initiative", "remediation_spend", "supplier_expedite",
                    "customer_credit", "budget_reallocation", "price_change"],
    },
    "customer_rescue": {
        "name": "Customer Rescue Agent", "sponsor": "Chief Customer Officer",
        "mission": "Stop customer-visible SLA breaches and protect recurring revenue by fixing and compensating "
                   "before the customer has to complain.",
        "tools": _SHARED + ["get_at_risk_accounts", "get_work_queue", "get_sla_exposure", "research_market"],
        "actions": ["executive_alert", "create_initiative", "prioritise_work", "customer_credit", "account_briefing"],
    },
    "growth_scout": {
        "name": "Growth Scout Agent", "sponsor": "CEO / CSO",
        "mission": "Turn the twin into a growth engine: pair spare capacity and strengths with live market "
                   "research to propose new revenue streams with a board-ready business case.",
        "tools": _SHARED + ["get_capacity_headroom", "get_market_landscape", "research_market", "simulate_decision"],
        "actions": ["executive_alert", "create_initiative", "growth_pilot", "reroute_capacity"],
    },
}
