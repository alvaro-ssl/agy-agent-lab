#!/usr/bin/env python3
"""Generates a synthetic, multi-layered digital twin of a company from `company_profile.yaml`.

Output (in company-twin/data/):
  twin.db          SQLite database the agent and the Decision Inbox read
  csv/<table>.csv  every table as CSV, to open in a spreadsheet
  twin_summary.md  a one-page narrative of the company and what is going wrong

Layers: 1 strategy & objectives · 2 organisation & people · 3 customers & market · 4 products & services ·
5 operations & processes · 6 supply chain & assets · 7 finance · 8 risk & governance — plus `signals`, the
anomalies the agent should find. The same company profile always produces the same twin.

Usage:  python generate_twin.py [--profile company_profile.yaml] [--out data]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import sqlite3
from datetime import date
from pathlib import Path

import yaml

from archetypes import ARCHETYPES, FIRST_NAMES, LAST_NAMES

HERE = Path(__file__).resolve().parent
MONTHS = 24


def month_list(n: int) -> list[str]:
    today = date.today()
    y, m = today.year, today.month - 1  # last full month
    if m == 0:
        y, m = y - 1, 12
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def ramp(base: float, final: float, i: int, n: int, start: int) -> float:
    """Linear move from base to final over the last (n - start) months."""
    if i < start:
        return base
    return base + (final - base) * (i - start + 1) / (n - start)


class Twin:
    def __init__(self, profile: dict):
        self.p = profile
        self.c = profile["company"]
        industry = self.c.get("industry", "retail_consumer")
        if industry not in ARCHETYPES:
            raise SystemExit(f"Unknown industry '{industry}'. Use one of: {', '.join(sorted(ARCHETYPES))}")
        self.a = ARCHETYPES[industry]
        seed = int(hashlib.sha256(self.c["name"].lower().encode()).hexdigest()[:8], 16)
        self.rng = random.Random(seed)
        self.months = month_list(MONTHS)
        self.rev = float(self.c["annual_revenue_m"]) * 1e6
        self.tables: dict[str, list[dict]] = {}
        self.signals: list[dict] = []

    # -- helpers ---------------------------------------------------------------
    def noise(self, spread: float = 0.03) -> float:
        return self.rng.uniform(1 - spread, 1 + spread)

    def person(self, used: set) -> str:
        """A synthetic name; first and last names are not reused until the pools run out."""
        firsts = [f for f in FIRST_NAMES if f not in {u.split(" ", 1)[0] for u in used}] or FIRST_NAMES
        lasts = [l for l in LAST_NAMES if l not in {u.split(" ", 1)[1] for u in used}] or LAST_NAMES
        while True:
            name = f"{self.rng.choice(firsts)} {self.rng.choice(lasts)}"
            if name not in used:
                used.add(name)
                return name

    def add(self, table: str, row: dict) -> None:
        self.tables.setdefault(table, []).append(row)

    def kpi(self, month: str, etype: str, eid: str, ename: str, metric: str, value: float) -> None:
        self.add("monthly_kpis", {"month": month, "entity_type": etype, "entity_id": eid, "entity_name": ename,
                                  "metric": metric, "value": round(value, 3)})

    def money(self, v: float) -> str:
        cur = self.c.get("currency", "EUR")
        sym = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF ", "SEK": "SEK ", "INR": "₹"}.get(cur, cur + " ")
        if abs(v) >= 1e9:
            return f"{sym}{v / 1e9:.1f}bn"
        if abs(v) >= 1e6:
            return f"{sym}{v / 1e6:.1f}m"
        if abs(v) >= 1e3:
            return f"{sym}{v / 1e3:.0f}k"
        return f"{sym}{v:.0f}"

    # -- layers ----------------------------------------------------------------
    def build(self) -> None:
        self.company_layer()
        self.strategy_layer()
        self.people_layer()
        self.customer_layer()
        self.product_layer()
        self.operations_layer()
        self.supply_layer()
        self.finance_layer()
        self.risk_layer()
        self.add_signals()

    def company_layer(self) -> None:
        c = self.c
        self.add("company", {
            "name": c["name"], "industry": c.get("industry"), "industry_label": self.a["label"],
            "description": c.get("description", ""), "headquarters": c.get("headquarters", ""),
            "website": c.get("website", ""), "currency": c.get("currency", "EUR"),
            "annual_revenue": self.rev, "employees": int(c.get("employees", 1000)),
            "revenue_growth_target_pct": float(c.get("revenue_growth_target_pct", 5)),
            "ebitda_margin_target_pct": float(c.get("ebitda_margin_target_pct", 10)),
            "first_month": self.months[0], "last_month": self.months[-1],
        })
        for i, r in enumerate(self.p.get("regions") or [{"name": "Home market", "share": 1.0}]):
            self.add("regions", {"region_id": f"R{i + 1}", "name": r["name"], "revenue_share": r["share"],
                                 "annual_revenue": round(self.rev * r["share"], 2)})
        used: set = set()
        roles = [("CEO", "Chief Executive Officer"), ("CFO", "Chief Financial Officer"),
                 ("COO", "Chief Operating Officer"), ("CCO", "Chief Commercial Officer"),
                 ("CHRO", "Chief People Officer"), ("CTO", "Chief Technology Officer")]
        self.leaders = {}
        for role, title in roles:
            name = self.person(used)
            self.leaders[role] = name
            self.add("leadership", {"role": role, "title": title, "name": name})
        self.used_names = used

    def strategy_layer(self) -> None:
        self.bus = []
        bus = self.p.get("business_units") or self.a["default_business_units"]
        total = sum(b["revenue_share"] for b in bus)
        for i, b in enumerate(bus):
            bu = {"bu_id": f"BU{i + 1}", "name": b["name"], "revenue_share": b["revenue_share"] / total,
                  "margin_pct": float(b.get("margin_pct", 30)), "products": b.get("products") or [b["name"]],
                  "head": self.person(self.used_names),
                  "growth_target_pct": float(self.c.get("revenue_growth_target_pct", 5)) + self.rng.uniform(-2, 3)}
            self.bus.append(bu)
            self.add("business_units", {"bu_id": bu["bu_id"], "name": bu["name"], "head": bu["head"],
                                        "revenue_share": round(bu["revenue_share"], 3),
                                        "gross_margin_target_pct": bu["margin_pct"],
                                        "growth_target_pct": round(bu["growth_target_pct"], 1)})
        for i, prio in enumerate(self.p.get("strategic_priorities") or []):
            self.add("objectives", {"objective_id": f"OBJ{i + 1}", "level": "company", "owner": self.leaders["CEO"],
                                    "objective": prio, "metric": "strategic priority", "target": None,
                                    "current": None, "status": "on track"})

    def people_layer(self) -> None:
        employees = int(self.c.get("employees", 1000))
        units = []
        for bu in self.bus:
            for f in self.a["functions"]:
                units.append((bu, f))
        corporate = ["Finance", "People & HR", "IT", "Legal & Compliance"]
        weights = [self.rng.uniform(0.6, 1.4) * (2.2 if f == self.a["functions"][0] else 1) for _, f in units]
        corp_share = 0.12
        total_w = sum(weights)
        self.org_units = []
        talent_bu = self.bus[1] if len(self.bus) > 1 else self.bus[0]
        n = MONTHS
        for idx, ((bu, f), w) in enumerate(zip(units, weights)):
            hc = max(8, int(employees * (1 - corp_share) * w / total_w))
            ou = {"org_unit_id": f"OU{idx + 1}", "name": f"{bu['name']} — {f}", "bu_id": bu["bu_id"], "function": f,
                  "headcount": hc, "manager": self.person(self.used_names)}
            talent = bu is talent_bu and f == self.a["talent_function"]
            base_attr = self.rng.uniform(8, 13)
            base_eng = self.rng.uniform(66, 76)
            ou["open_roles"] = 14 if talent else max(0, int(hc * self.rng.uniform(0.01, 0.04)))
            for i, m in enumerate(self.months):
                attr = ramp(base_attr, 22.0, i, n, n - 3) if talent else base_attr * self.noise(0.08)
                eng = ramp(base_eng, base_eng - 11, i, n, n - 3) if talent else base_eng * self.noise(0.02)
                self.kpi(m, "org_unit", ou["org_unit_id"], ou["name"], "attrition_annualised_pct", attr)
                self.kpi(m, "org_unit", ou["org_unit_id"], ou["name"], "engagement_score", eng)
            ou["attrition_annualised_pct"] = round(22.0 if talent else base_attr, 1)
            ou["engagement_score"] = round(base_eng - 11 if talent else base_eng, 1)
            ou["cost_per_fte"] = round(self.rng.uniform(52000, 98000), -2)
            if talent:
                self.talent_unit = ou
                self.talent_base = (base_attr, base_eng)
            self.org_units.append(ou)
            self.add("org_units", ou)
        for j, f in enumerate(corporate):
            hc = max(5, int(employees * corp_share / len(corporate)))
            ou = {"org_unit_id": f"OU{len(units) + j + 1}", "name": f"Group — {f}", "bu_id": None, "function": f,
                  "headcount": hc, "manager": self.person(self.used_names), "open_roles": int(hc * 0.02),
                  "attrition_annualised_pct": round(self.rng.uniform(7, 11), 1),
                  "engagement_score": round(self.rng.uniform(68, 77), 1), "cost_per_fte": round(self.rng.uniform(60000, 110000), -2)}
            self.org_units.append(ou)
            self.add("org_units", ou)

    def customer_layer(self) -> None:
        segs = self.p.get("customer_segments") or [
            {"name": s[0], "share": s[1], "churn_monthly_pct": s[2], "nps": s[3]} for s in self.a["segments"]]
        lo, hi = self.a["arpu_range"]
        self.segments = []
        n = MONTHS
        for i, s in enumerate(segs):
            arpu = self.rng.uniform(lo, hi)
            seg = {"segment_id": f"SEG{i + 1}", "name": s["name"], "revenue_share": s["share"],
                   "annual_revenue": round(self.rev * s["share"], 2),
                   "customers": int(self.rev * s["share"] / arpu), "arpu": round(arpu, 2),
                   "base_churn": float(s["churn_monthly_pct"]), "base_nps": float(s["nps"])}
            hit = i == 1
            for k, m in enumerate(self.months):
                churn = ramp(seg["base_churn"], seg["base_churn"] * 2.2, k, n, n - 3) if hit else seg["base_churn"] * self.noise(0.08)
                nps = ramp(seg["base_nps"], seg["base_nps"] - 12, k, n, n - 3) if hit else seg["base_nps"] + self.rng.uniform(-2, 2)
                self.kpi(m, "segment", seg["segment_id"], seg["name"], "churn_monthly_pct", churn)
                self.kpi(m, "segment", seg["segment_id"], seg["name"], "nps", nps)
            seg["churn_monthly_pct"] = round(seg["base_churn"] * (2.2 if hit else 1), 2)
            seg["nps"] = round(seg["base_nps"] - (12 if hit else 0), 1)
            self.segments.append(seg)
            self.add("customer_segments", {k: v for k, v in seg.items() if not k.startswith("base_")})

    def product_layer(self) -> None:
        lo, hi = self.a["unit_price_range"]
        self.products = []
        n = MONTHS
        for bu in self.bus:
            shares = [self.rng.uniform(0.6, 1.6) for _ in bu["products"]]
            shares[0] *= 1.6  # first product line is the largest
            total = sum(shares)
            for j, name in enumerate(bu["products"]):
                pid = f"PL{len(self.products) + 1}"
                margin = bu["margin_pct"] / 100 + self.rng.uniform(-0.03, 0.03)
                price = self.rng.uniform(lo, hi)
                prod = {"product_line_id": pid, "bu_id": bu["bu_id"], "name": name,
                        "revenue_share_of_bu": round(shares[j] / total, 3),
                        "annual_revenue": round(self.rev * bu["revenue_share"] * shares[j] / total, 2),
                        "list_price": round(price, 2), "base_margin": margin}
                hit = bu is self.bus[0] and j == 0
                cost_jump = 0.043 / (1 - margin)
                for k, m in enumerate(self.months):
                    unit_cost = price * (1 - margin) * (ramp(1, 1 + cost_jump, k, n, n - 3) if hit else self.noise(0.01))
                    gm = 100 * (1 - unit_cost / price)
                    self.kpi(m, "product_line", pid, name, "gross_margin_pct", gm)
                    self.kpi(m, "product_line", pid, name, "unit_cost", unit_cost)
                    self.kpi(m, "product_line", pid, name, "list_price", price)
                prod["gross_margin_pct"] = round(100 * (margin - (0.043 if hit else 0)), 1)
                if hit:
                    self.margin_product = prod
                self.products.append(prod)
                self.add("product_lines", {k: v for k, v in prod.items() if k != "base_margin"})

    def operations_layer(self) -> None:
        self.processes = []
        n = MONTHS
        for i, (name, unit, cycle, sla) in enumerate(self.a["processes"]):
            owner = self.bus[min(i, len(self.bus) - 1)]
            volume = max(50, int(self.rev / 1e6 * self.rng.uniform(4, 40)))
            proc = {"process_id": f"P{i + 1}", "name": name, "unit": unit, "owner_bu_id": owner["bu_id"],
                    "target_cycle_hours": cycle, "sla_target_pct": round(sla * 100, 1), "monthly_volume": volume}
            hit = i == 1
            base_sla = sla * 100 + 0.6
            for k, m in enumerate(self.months):
                ct = cycle * (ramp(1, 1.45, k, n, n - 3) if hit else self.rng.uniform(0.92, 1.05))
                backlog = volume * 0.18 * (ramp(1, 2.1, k, n, n - 3) if hit else self.noise(0.1))
                attain = ramp(base_sla, base_sla - 13, k, n, n - 3) if hit else min(99.8, base_sla + self.rng.uniform(-1, 0.8))
                self.kpi(m, "process", proc["process_id"], name, "cycle_time_hours", ct)
                self.kpi(m, "process", proc["process_id"], name, "backlog", backlog)
                self.kpi(m, "process", proc["process_id"], name, "sla_attainment_pct", attain)
                self.kpi(m, "process", proc["process_id"], name, "volume", volume * self.noise(0.06))
            proc["current_cycle_hours"] = round(cycle * (1.45 if hit else 1), 1)
            proc["current_sla_attainment_pct"] = round(base_sla - (13 if hit else 0), 1)
            self.processes.append(proc)
            self.add("processes", proc)

    def supply_layer(self) -> None:
        self.suppliers = []
        n = MONTHS
        for i, (name, category, typical_lt) in enumerate(self.a["suppliers"]):
            base_lt = typical_lt * self.rng.uniform(0.85, 1.15)
            spend = self.rev * (0.025 if i == 0 else self.rng.uniform(0.01, 0.05))
            sup = {"supplier_id": f"S{i + 1}", "name": name, "category": category,
                   "annual_spend": round(spend, 2),
                   "dependency_pct": 38.0 if i == 0 else round(self.rng.uniform(8, 30), 1),
                   "baseline_lead_time_days": round(base_lt, 1),
                   "supports_process_id": "P2" if i == 0 else None}
            hit = i == 0
            for k, m in enumerate(self.months):
                lt = base_lt * (ramp(1, 1.6, k, n, n - 3) if hit else self.noise(0.06))
                otd = ramp(96, 79, k, n, n - 3) if hit else self.rng.uniform(92, 98)
                self.kpi(m, "supplier", sup["supplier_id"], name, "lead_time_days", lt)
                self.kpi(m, "supplier", sup["supplier_id"], name, "on_time_delivery_pct", otd)
            sup["current_lead_time_days"] = round(base_lt * (1.6 if hit else 1), 1)
            sup["risk_score"] = 78 if hit else int(self.rng.uniform(15, 45))
            self.suppliers.append(sup)
            self.add("suppliers", sup)
        for region in self.tables["regions"]:
            for stype, per_region in self.a["site_types"]:
                count = max(1, int(per_region * region["revenue_share"] * 4))
                for _ in range(min(count, 6)):
                    self.add("sites", {"site_id": f"SITE{len(self.tables.get('sites', [])) + 1}",
                                       "name": f"{region['name']} {stype} {len([s for s in self.tables.get('sites', []) if s['region'] == region['name'] and s['type'] == stype]) + 1}",
                                       "type": stype, "region": region["name"],
                                       "utilization_pct": round(self.rng.uniform(62, 94), 1)})

    def finance_layer(self) -> None:
        n = MONTHS
        season = self.a["seasonality"]
        target_ebitda = float(self.c.get("ebitda_margin_target_pct", 10)) / 100
        hit_bu_rev = self.bus[1] if len(self.bus) > 1 else self.bus[0]
        self.fin = []
        for bu in self.bus:
            growth = bu["growth_target_pct"] / 100 - self.rng.uniform(0.005, 0.02)
            ebitda_m = target_ebitda * self.rng.uniform(0.8, 1.05)
            for k, m in enumerate(self.months):
                mon = int(m[5:7])
                years_back = (n - 1 - k) / 12
                base = self.rev * bu["revenue_share"] / 12 * season[mon - 1] / (sum(season) / 12)
                budget_rev = base * (1 + bu["growth_target_pct"] / 100) ** (-years_back + 1 / 12)
                revenue = base * (1 + growth) ** (-years_back + 1 / 12) * self.noise(0.015)
                if bu is hit_bu_rev and k >= n - 3:
                    revenue *= 1 - 0.015 * (k - n + 4)
                gm = bu["margin_pct"] / 100
                if bu is self.bus[0] and k >= n - 3:
                    gm -= 0.043 * self.margin_product["revenue_share_of_bu"] * (k - n + 4) / 3
                opex = revenue * (gm - ebitda_m)
                budget_opex = budget_rev * (bu["margin_pct"] / 100 - target_ebitda)
                marketing_budget = budget_opex * 0.18
                marketing = opex * 0.18
                if bu is self.bus[0] and k >= n - 6:
                    over = [0.06, 0.09, 0.12, 0.14, 0.15, 0.16][k - (n - 6)]
                    marketing = marketing_budget * (1 + over)
                    opex = opex - opex * 0.18 + marketing
                row = {"month": m, "bu_id": bu["bu_id"], "revenue": round(revenue, 2), "budget_revenue": round(budget_rev, 2),
                       "gross_margin_pct": round(gm * 100, 2), "cogs": round(revenue * (1 - gm), 2),
                       "opex": round(opex, 2), "budget_opex": round(budget_opex, 2),
                       "marketing_opex": round(marketing, 2), "budget_marketing_opex": round(marketing_budget, 2),
                       "ebitda": round(revenue * gm - opex, 2)}
                self.fin.append(row)
                self.add("monthly_financials", row)
        for k, m in enumerate(self.months):
            rev_m = sum(r["revenue"] for r in self.fin if r["month"] == m)
            self.kpi(m, "company", "GROUP", self.c["name"], "revenue", rev_m)
            self.kpi(m, "company", "GROUP", self.c["name"], "dso_days", self.rng.uniform(28, 46) + (4 if k >= n - 3 else 0))
            self.kpi(m, "company", "GROUP", self.c["name"], "dio_days", self.rng.uniform(25, 60))
            self.kpi(m, "company", "GROUP", self.c["name"], "dpo_days", self.rng.uniform(40, 65))
            self.kpi(m, "company", "GROUP", self.c["name"], "cash", self.rev * self.rng.uniform(0.07, 0.11))

        # Objectives with live status
        last12 = self.months[-12:]
        prev12 = self.months[-24:-12]
        for bu in self.bus:
            r_now = sum(r["revenue"] for r in self.fin if r["bu_id"] == bu["bu_id"] and r["month"] in last12)
            r_prev = sum(r["revenue"] for r in self.fin if r["bu_id"] == bu["bu_id"] and r["month"] in prev12)
            growth = 100 * (r_now / r_prev - 1)
            self.add("objectives", {"objective_id": f"OBJ-{bu['bu_id']}-G", "level": bu["name"], "owner": bu["head"],
                                    "objective": f"Grow {bu['name']} revenue", "metric": "revenue growth % (last 12m)",
                                    "target": round(bu["growth_target_pct"], 1), "current": round(growth, 1),
                                    "status": "on track" if growth >= bu["growth_target_pct"] - 0.5 else "at risk"})
        ebitda = sum(r["ebitda"] for r in self.fin if r["month"] in last12)
        revenue = sum(r["revenue"] for r in self.fin if r["month"] in last12)
        margin = 100 * ebitda / revenue
        self.add("objectives", {"objective_id": "OBJ-EBITDA", "level": "company", "owner": self.leaders["CFO"],
                                "objective": "Deliver EBITDA margin target", "metric": "EBITDA margin % (last 12m)",
                                "target": float(self.c.get("ebitda_margin_target_pct", 10)), "current": round(margin, 1),
                                "status": "on track" if margin >= float(self.c.get("ebitda_margin_target_pct", 10)) else "at risk"})

    def risk_layer(self) -> None:
        for i, (reg, scope) in enumerate(self.a["regulations"]):
            self.add("policies", {"policy_id": f"REG{i + 1}", "type": "regulation", "name": reg, "rule": scope})
        self.add("policies", {"policy_id": "DOA", "type": "internal", "name": "Delegation of authority",
                              "rule": "Decisions are taken within the limits in decision_rights.yaml; above them, the named executive approves."})
        for i, (title, layer) in enumerate(self.a["risks"]):
            self.add("risks", {"risk_id": f"RK{i + 1}", "title": title, "category": layer,
                               "likelihood": self.rng.randint(2, 4), "impact": self.rng.randint(3, 5),
                               "owner": self.leaders[self.rng.choice(["CFO", "COO", "CCO", "CTO"])], "status": "monitored"})

    def add_signals(self) -> None:
        bu0 = self.bus[0]
        seg = self.segments[1]
        proc = self.processes[1]
        sup = self.suppliers[0]
        ou = self.talent_unit
        fin_bu0 = [r for r in self.fin if r["bu_id"] == bu0["bu_id"]][-6:]
        overspend = sum(r["marketing_opex"] - r["budget_marketing_opex"] for r in fin_bu0)
        over_pct = 100 * overspend / sum(r["budget_marketing_opex"] for r in fin_bu0)
        mp = self.margin_product
        lt_up = 60  # planted increase (rounded lead times would show 55-65%)
        self.signals = [
            {"signal_id": "SIG1", "severity": "high", "layer": "supply chain", "entity_type": "supplier",
             "entity_id": sup["supplier_id"], "title": f"{sup['name']} lead times up {lt_up}%",
             "detail": f"Lead time {sup['baseline_lead_time_days']:.1f} → {sup['current_lead_time_days']:.1f} days over 3 months; on-time delivery 96% → 79%. "
                       f"{sup['dependency_pct']:.0f}% of {sup['category']} spend; it supports '{proc['name']}'.",
             "detected_days_ago": 11, "caused_by": None},
            {"signal_id": "SIG2", "severity": "high", "layer": "operations", "entity_type": "process",
             "entity_id": proc["process_id"], "title": f"{proc['name']} cycle time up 45%",
             "detail": f"{proc['target_cycle_hours']}h → {proc['current_cycle_hours']}h; backlog 2.1× normal; SLA attainment "
                       f"{proc['current_sla_attainment_pct'] + 13:.1f}% → {proc['current_sla_attainment_pct']:.1f}% (target {proc['sla_target_pct']}%).",
             "detected_days_ago": 8, "caused_by": "SIG1"},
            {"signal_id": "SIG3", "severity": "high", "layer": "customers", "entity_type": "segment",
             "entity_id": seg["segment_id"], "title": f"Churn in {seg['name']} up from {seg['base_churn']:.1f}% to {seg['churn_monthly_pct']:.1f}% a month",
             "detail": f"NPS {seg['base_nps']:.0f} → {seg['nps']:.0f}; complaints cite '{proc['name']}' delays. "
                       f"{seg['customers']:,} customers, {self.money(seg['annual_revenue'])} annual revenue.",
             "detected_days_ago": 5, "caused_by": "SIG2"},
            {"signal_id": "SIG4", "severity": "medium", "layer": "products", "entity_type": "product_line",
             "entity_id": mp["product_line_id"], "title": f"Gross margin on {mp['name']} down 4.3 pts in 3 months",
             "detail": f"Unit cost up {100 * 0.043 / (1 - mp['base_margin']):.1f}% while the list price is unchanged; "
                       f"{mp['name']} is the largest line in {bu0['name']} ({self.money(mp['annual_revenue'])} a year).",
             "detected_days_ago": 14, "caused_by": None},
            {"signal_id": "SIG5", "severity": "medium", "layer": "people", "entity_type": "org_unit",
             "entity_id": ou["org_unit_id"], "title": f"{ou['name']} attrition at 22% (annualised)",
             "detail": f"Up from {self.talent_base[0]:.0f}%; {ou['open_roles']} open roles; engagement {self.talent_base[1]:.0f} → {ou['engagement_score']:.0f}/100.",
             "detected_days_ago": 20, "caused_by": None},
            {"signal_id": "SIG6", "severity": "medium", "layer": "finance", "entity_type": "business_unit",
             "entity_id": bu0["bu_id"], "title": f"{bu0['name']} marketing {over_pct:.0f}% over budget (last 6 months)",
             "detail": f"{self.money(overspend)} above plan; spend rising every month while revenue tracks budget.",
             "detected_days_ago": 3, "caused_by": None},
        ]
        for s in self.signals:
            self.add("signals", s)
        self.add("risks", {"risk_id": f"RK{len(self.tables['risks']) + 1}",
                           "title": f"Dependency on {sup['name']} ({sup['dependency_pct']:.0f}% of {sup['category']})",
                           "category": "Supply chain", "likelihood": 4, "impact": 4, "owner": self.leaders["COO"],
                           "status": "escalated"})

    # -- output ----------------------------------------------------------------
    def write(self, out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "csv").mkdir(exist_ok=True)
        db_path = out / "twin.db"
        if db_path.exists():
            db_path.unlink()
        conn = sqlite3.connect(db_path)
        for table, rows in self.tables.items():
            cols = list(dict.fromkeys(k for r in rows for k in r))
            for r in rows:
                for k in cols:
                    r.setdefault(k, None)
                    if isinstance(r[k], list):
                        r[k] = ", ".join(map(str, r[k]))
            conn.execute(f"CREATE TABLE {table} ({', '.join(cols)})")
            conn.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in cols)})", [[r[k] for k in cols] for r in rows])
            with open(out / "csv" / f"{table}.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                w.writeheader()
                w.writerows(rows)
        conn.executescript(
            """
            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY, action_type TEXT, target TEXT, amount REAL, unit TEXT,
                rationale TEXT, approver_role TEXT, approver_name TEXT, requested_by TEXT, requested_at TEXT,
                status TEXT, decided_by TEXT, decided_at TEXT, consumed INTEGER DEFAULT 0
            );
            CREATE TABLE actions_log (
                action_id TEXT PRIMARY KEY, action_type TEXT, target TEXT, amount REAL, unit TEXT, rationale TEXT,
                mode TEXT, authorised_by TEXT, approval_id TEXT, executed_at TEXT
            );
            CREATE INDEX kpi_lookup ON monthly_kpis (entity_type, entity_id, metric);
            """
        )
        conn.commit()
        conn.close()
        (out / "twin_summary.md").write_text(self.summary())

    def summary(self) -> str:
        c = self.c
        last12 = self.months[-12:]
        rev = sum(r["revenue"] for r in self.fin if r["month"] in last12)
        ebitda = sum(r["ebitda"] for r in self.fin if r["month"] in last12)
        lines = [
            f"# {c['name']} — digital twin summary (synthetic)",
            "",
            f"{c.get('description', '')}  ",
            f"Industry: {self.a['label']} · HQ: {c.get('headquarters', '')} · Employees: {int(c.get('employees', 0)):,} · "
            f"Revenue (last 12 months): {self.money(rev)} · EBITDA margin: {100 * ebitda / rev:.1f}% "
            f"(target {c.get('ebitda_margin_target_pct')}%)",
            "",
            "## Business units",
            *[f"- **{b['name']}** ({b['head']}) — {100 * b['revenue_share']:.0f}% of revenue; products: {', '.join(b['products'])}" for b in self.bus],
            "",
            "## Leadership (synthetic names)",
            *[f"- {r['role']}: {r['name']}" for r in self.tables["leadership"]],
            "",
            "## Signals the agent should investigate",
            *[f"- **{s['signal_id']} [{s['severity']}] {s['title']}** — {s['detail']}" for s in self.signals],
            "",
            f"Data covers {self.months[0]} to {self.months[-1]}. Tables: {', '.join(sorted(self.tables))}.",
        ]
        return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default=str(HERE / "company_profile.yaml"))
    parser.add_argument("--out", default=str(HERE / "data"))
    args = parser.parse_args()
    profile = yaml.safe_load(Path(args.profile).read_text())
    twin = Twin(profile)
    twin.build()
    twin.write(Path(args.out))
    rows = sum(len(r) for r in twin.tables.values())
    print(f"Digital twin for {twin.c['name']} ({twin.a['label']}): {len(twin.tables)} tables, {rows:,} rows -> {args.out}")
    print(f"Open {Path(args.out) / 'twin_summary.md'} or run the Decision Inbox: .venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090")


if __name__ == "__main__":
    main()
