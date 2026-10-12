#!/usr/bin/env python3
"""Generates a synthetic, multi-layered digital twin of a company from `company_profile.yaml`.

Output (in company-twin/data/):
  twin.db          SQLite database the agent and the Decision Inbox read
  csv/<table>.csv  every table as CSV, to open in a spreadsheet
  twin_summary.md  a one-page narrative: what is going well, what to watch, and where the opportunities are

Layers: 1 strategy & objectives · 2 organisation & people · 3 customers & market · 4 products & services ·
5 operations & processes · 6 supply chain & assets · 7 finance · 8 risk & governance — plus `signals`: strengths,
risks to watch and opportunities the agent should find. The same company profile always produces the same twin.
People appear only as roles (e.g. "Chief Financial Officer"), and customers as segment labels — never names.

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

from archetypes import ARCHETYPES, EXTRAS, FX_PER_EUR, REGION_CURRENCY

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
        self.rng2 = random.Random(seed + 1)  # separate stream for the agent-type layers, so core data stays stable
        self.x = EXTRAS[industry]
        self.base = self.c.get("currency", "EUR")
        self.months = month_list(MONTHS)
        self.rev = float(self.c["annual_revenue_m"]) * 1e6
        self.tables: dict[str, list[dict]] = {}
        self.signals: list[dict] = []

    # -- helpers ---------------------------------------------------------------
    def noise(self, spread: float = 0.03) -> float:
        return self.rng.uniform(1 - spread, 1 + spread)

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
        # Layers used by the four agent types (separate random stream)
        self.leadership_extras()
        self.fx_layer()
        self.systems_layer()
        self.accounts_layer()
        self.dependencies_and_buffers()
        self.playbooks_and_costs()
        self.growth_layer()
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
        roles = [("CEO", "Chief Executive Officer"), ("CFO", "Chief Financial Officer"),
                 ("COO", "Chief Operating Officer"), ("CCO", "Chief Customer & Commercial Officer"),
                 ("CHRO", "Chief People Officer"), ("CTO", "Chief Technology Officer")]
        self.leaders = {}
        for role, title in roles:
            self.leaders[role] = title  # roles only: the twin never holds people's names
            self.add("leadership", {"role": role, "title": title, "name": title})

    def strategy_layer(self) -> None:
        self.bus = []
        bus = self.p.get("business_units") or self.a["default_business_units"]
        total = sum(b["revenue_share"] for b in bus)
        for i, b in enumerate(bus):
            bu = {"bu_id": f"BU{i + 1}", "name": b["name"], "revenue_share": b["revenue_share"] / total,
                  "margin_pct": float(b.get("margin_pct", 30)), "products": b.get("products") or [b["name"]],
                  "head": f"Head of {b['name']}",
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
                  "headcount": hc, "manager": f"Head of {f}, {bu['name']}"}
            talent = bu is talent_bu and f == self.a["talent_function"]
            base_attr = self.rng.uniform(8, 13)
            base_eng = self.rng.uniform(66, 76)
            ou["open_roles"] = 8 if talent else max(0, int(hc * self.rng.uniform(0.01, 0.04)))
            for i, m in enumerate(self.months):
                attr = ramp(base_attr, 15.0, i, n, n - 3) if talent else base_attr * self.noise(0.08)
                eng = ramp(base_eng, base_eng - 4, i, n, n - 3) if talent else base_eng * self.noise(0.02)
                self.kpi(m, "org_unit", ou["org_unit_id"], ou["name"], "attrition_annualised_pct", attr)
                self.kpi(m, "org_unit", ou["org_unit_id"], ou["name"], "engagement_score", eng)
            ou["attrition_annualised_pct"] = round(15.0 if talent else base_attr, 1)
            ou["engagement_score"] = round(base_eng - 4 if talent else base_eng, 1)
            ou["cost_per_fte"] = round(self.rng.uniform(52000, 98000), -2)
            if talent:
                self.talent_unit = ou
                self.talent_base = (base_attr, base_eng)
            self.org_units.append(ou)
            self.add("org_units", ou)
        for j, f in enumerate(corporate):
            hc = max(5, int(employees * corp_share / len(corporate)))
            ou = {"org_unit_id": f"OU{len(units) + j + 1}", "name": f"Group — {f}", "bu_id": None, "function": f,
                  "headcount": hc, "manager": f"Group head of {f}", "open_roles": int(hc * 0.02),
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
            hit, loyal = i == 1, i == 0
            for k, m in enumerate(self.months):
                churn = (ramp(seg["base_churn"], seg["base_churn"] * 1.5, k, n, n - 3) if hit
                         else ramp(seg["base_churn"], seg["base_churn"] * 0.8, k, n, n - 6) if loyal
                         else seg["base_churn"] * self.noise(0.08))
                nps = (ramp(seg["base_nps"], seg["base_nps"] - 6, k, n, n - 3) if hit
                       else ramp(seg["base_nps"], seg["base_nps"] + 7, k, n, n - 6) if loyal
                       else seg["base_nps"] + self.rng.uniform(-2, 2))
                self.kpi(m, "segment", seg["segment_id"], seg["name"], "churn_monthly_pct", churn)
                self.kpi(m, "segment", seg["segment_id"], seg["name"], "nps", nps)
            seg["churn_monthly_pct"] = round(seg["base_churn"] * (1.5 if hit else 0.8 if loyal else 1), 2)
            seg["nps"] = round(seg["base_nps"] - 6 if hit else seg["base_nps"] + 7 if loyal else seg["base_nps"], 1)
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
            hit, improving = i == 1, i == 0
            base_sla = sla * 100 + 0.6
            for k, m in enumerate(self.months):
                ct = cycle * (ramp(1, 1.3, k, n, n - 3) if hit else ramp(1, 0.86, k, n, n - 6) if improving else self.rng.uniform(0.92, 1.05))
                backlog = volume * 0.18 * (ramp(1, 1.6, k, n, n - 3) if hit else self.noise(0.1))
                attain = (ramp(base_sla, base_sla - 7, k, n, n - 3) if hit
                          else min(99.8, ramp(base_sla, base_sla + 1.4, k, n, n - 6)) if improving
                          else min(99.8, base_sla + self.rng.uniform(-1, 0.8)))
                self.kpi(m, "process", proc["process_id"], name, "cycle_time_hours", ct)
                self.kpi(m, "process", proc["process_id"], name, "backlog", backlog)
                self.kpi(m, "process", proc["process_id"], name, "sla_attainment_pct", attain)
                self.kpi(m, "process", proc["process_id"], name, "volume", volume * self.noise(0.06))
            proc["current_cycle_hours"] = round(cycle * (1.3 if hit else 0.86 if improving else 1), 1)
            proc["current_sla_attainment_pct"] = round(base_sla - 7 if hit else min(99.8, base_sla + 1.4) if improving else base_sla, 1)
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
                lt = base_lt * (ramp(1, 1.35, k, n, n - 3) if hit else self.noise(0.06))
                otd = ramp(96, 86, k, n, n - 3) if hit else self.rng.uniform(92, 98)
                self.kpi(m, "supplier", sup["supplier_id"], name, "lead_time_days", lt)
                self.kpi(m, "supplier", sup["supplier_id"], name, "on_time_delivery_pct", otd)
            sup["current_lead_time_days"] = round(base_lt * (1.35 if hit else 1), 1)
            sup["risk_score"] = 64 if hit else int(self.rng.uniform(15, 45))
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
        self.strong_bu = self.bus[-1] if len(self.bus) > 2 else self.bus[0]
        for bu in self.bus:
            # The unit hit by the disruption trails its plan; the others are on or ahead of plan.
            behind = bu is hit_bu_rev
            growth = bu["growth_target_pct"] / 100 + (-self.rng.uniform(0.003, 0.01) if behind
                                                       else 0.025 if bu is self.strong_bu else self.rng.uniform(0.002, 0.01))
            ebitda_m = target_ebitda * self.rng.uniform(0.95, 1.03)
            for k, m in enumerate(self.months):
                mon = int(m[5:7])
                years_back = (n - 1 - k) / 12
                base = self.rev * bu["revenue_share"] / 12 * season[mon - 1] / (sum(season) / 12)
                budget_rev = base * (1 + bu["growth_target_pct"] / 100) ** (-years_back + 1 / 12)
                revenue = base * (1 + growth) ** (-years_back + 1 / 12) * self.noise(0.015)
                if bu is hit_bu_rev and k >= n - 3:
                    revenue *= 1 - 0.006 * (k - n + 4)
                gm = bu["margin_pct"] / 100
                if bu is self.bus[0] and k >= n - 3:
                    gm -= 0.043 * self.margin_product["revenue_share_of_bu"] * (k - n + 4) / 3
                opex = revenue * (gm - ebitda_m)
                budget_opex = budget_rev * (bu["margin_pct"] / 100 - target_ebitda)
                marketing_budget = budget_opex * 0.18
                marketing = opex * 0.18
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


    # -- layers for the four agent types -------------------------------------------
    def to_base(self, amount: float, currency: str) -> float:
        return amount / self.fx_now[currency]

    def leadership_extras(self) -> None:
        for role, title in [("CRO", "Chief Risk Officer"), ("CSO", "Chief Strategy Officer")]:
            self.leaders[role] = title
            self.add("leadership", {"role": role, "title": title, "name": title})
        for ou in self.tables["org_units"]:
            talent = ou is getattr(self, "talent_unit", None)
            ou["utilization_pct"] = 92.0 if talent else round(self.rng2.uniform(72, 90), 1)

    def fx_layer(self) -> None:
        base_eur = FX_PER_EUR.get(self.base, 1.0)
        currencies = {self.base}
        for r in self.tables["regions"]:
            name = r["name"].lower()
            cur = next((c for keys, c in REGION_CURRENCY if any(k == name or k in name.split() or name.startswith(k) for k in keys)), None)
            r["currency"] = cur or self.base
            currencies.add(r["currency"])
        self.fx_now = {}
        for cur in sorted(currencies):
            per_base = FX_PER_EUR.get(cur, 1.0) / base_eur
            phase = self.rng2.uniform(0, 6)
            for k, m in enumerate(self.months):
                rate = per_base * (1 + 0.03 * __import__("math").sin(k / 4 + phase)) * self.rng2.uniform(0.995, 1.005)
                if cur == self.base:
                    rate = 1.0
                self.add("fx_rates", {"month": m, "currency": cur, "units_per_base": round(rate, 5), "base_currency": self.base})
            self.fx_now[cur] = [r for r in self.tables["fx_rates"] if r["currency"] == cur][-1]["units_per_base"]

    def systems_layer(self) -> None:
        self.systems = []
        n = MONTHS
        for i, (name, stype, headroom, spof, procs) in enumerate(self.x["systems"]):
            sysrow = {"system_id": f"SYS{i + 1}", "name": name, "type": stype,
                      "capacity_headroom_pct": float(headroom), "single_point_of_failure": int(spof),
                      "has_failover": int(not spof),
                      "supports_processes": ", ".join(f"P{p + 1}" for p in procs if p < len(self.processes)),
                      "availability_30d_pct": round(99.9 - (0.25 if spof else self.rng2.uniform(0, 0.08)), 2)}
            for k, m in enumerate(self.months):
                h = ramp(34.0, headroom, k, n, n - 6) if spof else headroom * self.rng2.uniform(0.9, 1.1)
                self.kpi(m, "system", sysrow["system_id"], name, "capacity_headroom_pct", h)
            self.systems.append(sysrow)
            self.add("systems", sysrow)
        self.spof = next(s for s in self.systems if s["single_point_of_failure"])

    def accounts_layer(self) -> None:
        segs = [self.segments[i] for i in self.x["account_segments"] if i < len(self.segments)] or self.segments[-1:]
        pool = min(sum(s["annual_revenue"] for s in segs) * 0.35, self.rev * 0.2)
        n_acc = 36
        weights = [1 / (i + 1) ** 0.9 for i in range(n_acc)]
        total_w = sum(weights)
        regions = self.tables["regions"]
        affected_ranks = [0, 2, 3, 5, 8, 11, 14]
        renewing = {0: 38, 2: 21, 3: 55, 5: 47, 8: 29}
        proc = self.processes[1]
        self.accounts, self.affected = [], []
        for i in range(n_acc):
            region = self.rng2.choices(regions, weights=[r["revenue_share"] for r in regions])[0]
            foreign = [r for r in regions if r["currency"] != self.base]
            if i in (2, 5) and foreign:  # make the finance story multi-currency
                region = foreign[(i // 3) % len(foreign)]
            cur = region["currency"]
            acv_base = pool * weights[i] / total_w
            acv = acv_base * self.fx_now[cur]
            affected = i in affected_ranks
            seg = segs[i % len(segs)]
            kind = self.rng2.choice(self.x["account_suffixes"])
            tier = "Platinum" if i < 8 else "Gold" if i < 22 else "Silver"
            # A descriptive label, never a company name: "Platinum account · Pharmacies · Germany"
            label = f"{tier} account · {kind} · {region['name']}"
            same = sum(1 for a in self.accounts if a["name"].startswith(label))
            label = f"{label} {same + 1}" if same else label
            penalty_h = acv * 0.00002  # ~0.002% of contract value per hour in breach
            hours = 24 * self.rng2.uniform(5, 9) if affected else 0
            acc = {"account_id": f"ACC{i + 1:03d}", "name": label, "industry": kind,
                   "segment_id": seg["segment_id"], "region": region["name"], "currency": cur,
                   "tier": tier,
                   "annual_contract_value": round(acv, 2), "annual_contract_value_base": round(acv_base, 2),
                   "renewal_in_days": renewing.get(i, int(self.rng2.uniform(75, 360)) if not affected else int(self.rng2.uniform(90, 200))),
                   "health_score": round(self.rng2.uniform(55, 66) if affected else self.rng2.uniform(70, 92)),
                   "nps": round(self.rng2.uniform(14, 26) if affected else self.rng2.uniform(30, 58)),
                   "churn_risk_pct": round(self.rng2.uniform(22, 38) if affected else self.rng2.uniform(4, 14), 1),
                   "account_owner": f"Account director, {region['name']}",
                   "contact_role": self.rng2.choice(self.x["contact_roles"]),
                   "sla_penalty_per_hour": round(penalty_h, 2), "sla_penalty_cap": round(acv * 0.15, 2),
                   "sla_hours_in_breach": round(hours, 1), "sla_penalty_accrued": round(penalty_h * hours, 2),
                   "goodwill_credit_ceiling": round(acv * 0.02, 2)}
            self.accounts.append(acc)
            self.add("accounts", acc)
            if affected:
                self.affected.append(acc)
                self.add("work_queue", {"account_id": acc["account_id"], "process_id": proc["process_id"],
                                        "items_open": int(self.rng2.uniform(14, 80)),
                                        "items_breaching_sla": int(self.rng2.uniform(9, 40)),
                                        "oldest_item_age_hours": round(proc["target_cycle_hours"] * self.rng2.uniform(1.7, 2.6), 1),
                                        "sla_hours": proc["target_cycle_hours"],
                                        "value_at_risk": round(acv * self.rng2.uniform(0.01, 0.03), 2), "currency": cur,
                                        "blocked_by": self.suppliers[0]["supplier_id"], "status": "breaching SLA"})
            elif self.rng2.random() < 0.5:
                p = self.rng2.choice([p for p in self.processes if p is not proc])
                self.add("work_queue", {"account_id": acc["account_id"], "process_id": p["process_id"],
                                        "items_open": int(self.rng2.uniform(1, 12)), "items_breaching_sla": 0,
                                        "oldest_item_age_hours": round(p["target_cycle_hours"] * self.rng2.uniform(0.2, 0.9), 1),
                                        "sla_hours": p["target_cycle_hours"],
                                        "value_at_risk": 0.0, "currency": cur, "blocked_by": None, "status": "on track"})
        burn_h = sum(self.to_base(a["sla_penalty_per_hour"], a["currency"]) for a in self.affected)
        self.add("incidents", {"incident_id": "INC-301", "severity": "SEV2", "status": "ongoing",
                               "title": f"{proc['name']} delays — {self.suppliers[0]['name']} capacity shortfall",
                               "process_id": proc["process_id"], "system_id": None, "started_days_ago": 8,
                               "resolved_days_ago": None, "accounts_affected": len(self.affected),
                               "sla_penalties_per_hour_base": round(burn_h, 2)})
        self.add("incidents", {"incident_id": "INC-288", "severity": "SEV2", "status": "resolved",
                               "title": f"{self.spof['name']} slowdown at the month-end peak",
                               "process_id": self.spof["supports_processes"].split(", ")[0], "system_id": self.spof["system_id"],
                               "started_days_ago": 26, "resolved_days_ago": 26, "accounts_affected": 11,
                               "sla_penalties_per_hour_base": 0.0})
        self.add("incidents", {"incident_id": "INC-276", "severity": "SEV3", "status": "resolved",
                               "title": f"{self.processes[2]['name']} backlog after a release", "process_id": self.processes[2]["process_id"],
                               "system_id": None, "started_days_ago": 41, "resolved_days_ago": 39, "accounts_affected": 2,
                               "sla_penalties_per_hour_base": 0.0})

    def dependencies_and_buffers(self) -> None:
        s1 = self.suppliers[0]
        alt = {"supplier_id": f"S{len(self.suppliers) + 1}", "name": f"Alternative {s1['category'].lower()} provider",
               "category": s1["category"], "annual_spend": 0.0, "dependency_pct": 0.0,
               "baseline_lead_time_days": round(s1["baseline_lead_time_days"] * 1.1, 1), "supports_process_id": None,
               "current_lead_time_days": round(s1["baseline_lead_time_days"] * 1.1, 1), "risk_score": 25,
               "status": "qualified standby", "cost_premium_pct": 8.0}
        for sup in self.suppliers:
            sup.setdefault("status", "active")
            sup.setdefault("cost_premium_pct", 0.0)
        self.suppliers.append(alt)
        self.add("suppliers", alt)
        self.alt_supplier = alt
        sites = self.tables["sites"]
        for i, proc in enumerate(self.processes):
            for sysrow in self.systems:
                if proc["process_id"] in sysrow["supports_processes"].split(", "):
                    self.add("dependencies", {"from_type": "process", "from_id": proc["process_id"], "from_name": proc["name"],
                                              "to_type": "system", "to_id": sysrow["system_id"], "to_name": sysrow["name"],
                                              "criticality": "high" if sysrow["single_point_of_failure"] else "medium",
                                              "has_alternative": sysrow["has_failover"], "alternative": None if sysrow["single_point_of_failure"] else "failover region"})
            sup = s1 if i == 1 else self.suppliers[1 + (i % (len(self.suppliers) - 2))]
            self.add("dependencies", {"from_type": "process", "from_id": proc["process_id"], "from_name": proc["name"],
                                      "to_type": "supplier", "to_id": sup["supplier_id"], "to_name": sup["name"],
                                      "criticality": "high" if i == 1 else "medium", "has_alternative": 1,
                                      "alternative": alt["name"] if i == 1 else "secondary supplier"})
            ou = next((o for o in self.org_units if o["bu_id"] == proc["owner_bu_id"]), self.org_units[0])
            self.add("dependencies", {"from_type": "process", "from_id": proc["process_id"], "from_name": proc["name"],
                                      "to_type": "org_unit", "to_id": ou["org_unit_id"], "to_name": ou["name"],
                                      "criticality": "medium", "has_alternative": 0, "alternative": None})
            if i < 2:
                typed = [st for st in sites if st["type"] == self.a["site_types"][-1][0]]
                if typed:
                    main = max(typed, key=lambda st: st["utilization_pct"])
                    backup = next((st for st in typed if st is not main), None)
                    self.add("dependencies", {"from_type": "process", "from_id": proc["process_id"], "from_name": proc["name"],
                                              "to_type": "site", "to_id": main["site_id"], "to_name": main["name"],
                                              "criticality": "medium", "has_alternative": int(backup is not None),
                                              "alternative": backup["name"] if backup else None})

        def buffer(name, etype, eid, unit, current, threshold, per_week, regulatory, signal=None):
            falling = per_week < 0
            gap = current - threshold
            days = 0.0 if gap <= 0 else (round(gap / -per_week * 7, 1) if falling else None)
            self.add("buffers", {"buffer_id": f"B{len(self.tables.get('buffers', [])) + 1}", "name": name, "entity_type": etype,
                                 "entity_id": eid, "unit": unit, "current": round(current, 2), "threshold": threshold,
                                 "change_per_week": round(per_week, 3), "days_to_breach": days, "regulatory": int(regulatory),
                                 "linked_signal": signal})

        buffer(f"{self.spof['name']} capacity headroom", "system", self.spof["system_id"], "%", self.spof["capacity_headroom_pct"], 5.0, -3.0, False, "SIG9")
        proc = self.processes[1]
        buffer(f"{proc['name']} SLA attainment vs contracts", "process", proc["process_id"], "%", proc["current_sla_attainment_pct"], 90.0, -1.5, False, "SIG2")
        buffer(f"Days of cover — {s1['category'].lower()}", "supplier", s1["supplier_id"], "days", 4.2, 3.0, -0.4, False, "SIG1")
        name, unit, cur, thr, monthly, _ = self.x["regulatory_buffer"]
        buffer(name, "company", "GROUP", unit, cur, thr, monthly / 4.3, True)
        t = self.talent_unit
        buffer(f"{t['name']} workload capacity", "org_unit", t["org_unit_id"], "% spare", 100 - 92.0, 0.0, -0.5, False)

    def playbooks_and_costs(self) -> None:
        s1, proc, alt = self.suppliers[0], self.processes[1], self.alt_supplier
        ops_unit = next((o for o in self.org_units if o["bu_id"] == proc["owner_bu_id"]), self.org_units[0])
        burst_h = round(12 * 1.5 * ops_unit["cost_per_fte"] / 1800, 2)
        rows = [
            ("Expedite with " + s1["name"], "supplier_expedite", "supplier", s1["supplier_id"], s1["name"], s1["annual_spend"] * 0.005, 0.0, 14, 80, "SIG1, SIG2"),
            (f"Shift 40% of volume to {alt['name']}", "activate_backup_supplier", "supplier", alt["supplier_id"], alt["name"], s1["annual_spend"] * 0.001, s1["annual_spend"] * 0.4 * 0.08 / 365, 21, 60, "SIG1"),
            (f"Defer non-critical work in {proc['name']}", "throttle_noncritical", "process", proc["process_id"], proc["name"], 0.0, 0.0, 1, 15, "SIG2"),
            (f"Burst capacity for {ops_unit['name']}", "remediation_spend", "org_unit", ops_unit["org_unit_id"], ops_unit["name"], 0.0, burst_h * 24, 2, 35, "SIG2, SIG8"),
            (f"Prioritise Platinum & Gold accounts in {proc['name']}", "prioritise_work", "process", proc["process_id"], proc["name"], 0.0, 0.0, 1, 25, "SIG7, SIG8"),
            (f"Add capacity and failover to {self.spof['name']}", "system_capacity_increase", "system", self.spof["system_id"], self.spof["name"], self.rev * 0.00004, 0.0, 7, 90, "SIG9"),
            ("Goodwill credits for affected key accounts", "customer_credit", "accounts", "affected", f"{len(self.affected)} key accounts",
             sum(self.to_base(a["goodwill_credit_ceiling"], a["currency"]) for a in self.affected) * 0.5, 0.0, 0, 30, "SIG7"),
        ]
        for i, (name, action, ttype, tid, tname, one_off, daily, days, reduction, signals) in enumerate(rows):
            self.add("mitigation_playbooks", {"playbook_id": f"PB{i + 1}", "name": name, "action_type": action,
                                              "target_type": ttype, "target_id": tid, "target_name": tname,
                                              "one_off_cost_base": round(one_off, 2), "daily_cost_base": round(daily, 2),
                                              "time_to_effect_days": days, "burn_reduction_pct": reduction, "addresses": signals})
        seg = self.segments[1]
        churn_h = seg["annual_revenue"] / 8760 * 0.012 * 0.5
        for name, value, unit in [
            ("burst_capacity_per_hour", burst_h, f"{self.base}/hour"),
            ("rework_cost_per_item", round(self.rng2.uniform(18, 60), 2), f"{self.base}/item"),
            ("revenue_at_risk_per_hour_from_churn", round(churn_h, 2), f"{self.base}/hour"),
            ("inventory_carrying_cost_pct_per_year", 9.0, "%"),
            ("discount_rate_pct_per_year", 10.0, "%"),
        ]:
            self.add("cost_rates", {"name": name, "value": value, "unit": unit})

    def growth_layer(self) -> None:
        regions = sorted(self.tables["regions"], key=lambda r: -r["revenue_share"])[:4]
        target_region = regions[1] if len(regions) > 1 else regions[0]
        stype = self.a["site_types"][-1][0]
        for st in self.tables["sites"]:
            if st["region"] == target_region["name"] and st["type"] == stype:
                st["utilization_pct"] = round(self.rng2.uniform(55, 60), 1)
        best = self.x["opportunities"][3]
        margins = [b["margin_pct"] for b in self.bus]
        for r in regions:
            for j, opp in enumerate(self.x["opportunities"]):
                planted = r is target_region and opp == best
                self.add("market_landscape", {
                    "region": r["name"], "opportunity": opp,
                    "market_size_base": round(self.rev * (0.075 if planted else self.rng2.uniform(0.01, 0.06)), -3),
                    "growth_pct_per_year": round(18.0 if planted else self.rng2.uniform(2, 14), 1),
                    "our_share_pct": round(0.0 if j >= 2 else self.rng2.uniform(0.5, 4), 1),
                    "leading_competitor": self.rng2.choice(self.x["competitors"]),
                    "leading_competitor_share_pct": round(self.rng2.uniform(12, 38), 1),
                    "estimated_margin_pct": round(max(margins) + 4 if planted else self.rng2.uniform(min(margins) - 6, max(margins)), 1),
                    "capability_fit": "high" if planted else self.rng2.choice(["medium", "low", "medium"]),
                })
        self.growth = {"region": target_region["name"], "opportunity": best, "site_type": stype}
        for theme, pidx in self.x["friction_themes"]:
            proc = self.processes[min(pidx, len(self.processes) - 1)]
            hot = proc is self.processes[1]
            self.add("friction_points", {"theme": theme, "process_id": proc["process_id"],
                                         "segment_id": self.segments[1]["segment_id"] if hot else self.rng2.choice(self.segments)["segment_id"],
                                         "mentions_last_30d": int(self.rng2.uniform(900, 2400) if hot else self.rng2.uniform(80, 600)),
                                         "trend_pct": round(self.rng2.uniform(110, 160) if hot else self.rng2.uniform(-15, 20), 1)})

    def risk_layer(self) -> None:
        for i, (reg, scope) in enumerate(self.a["regulations"]):
            self.add("policies", {"policy_id": f"REG{i + 1}", "type": "regulation", "name": reg, "rule": scope})
        self.add("policies", {"policy_id": "DOA", "type": "internal", "name": "Delegation of authority",
                              "rule": "Decisions are taken within the limits in decision_rights.yaml; above them, the human in the loop named there approves."})
        for i, (title, layer) in enumerate(self.a["risks"]):
            self.add("risks", {"risk_id": f"RK{i + 1}", "title": title, "category": layer,
                               "likelihood": self.rng.randint(2, 4), "impact": self.rng.randint(3, 5),
                               "owner": self.leaders[self.rng.choice(["CFO", "COO", "CCO", "CTO"])], "status": "monitored"})

    def add_signals(self) -> None:
        """A balanced picture: strengths, risks to watch and opportunities. SIG1 -> SIG2 -> SIG3/SIG7/SIG8 is the live
        supplier -> process -> customer chain the four agents work on; SIG4-SIG6 are strengths; SIG10 is a growth play."""
        seg, loyal = self.segments[1], self.segments[0]
        proc, good_proc = self.processes[1], self.processes[0]
        sup = self.suppliers[0]
        strong = self.strong_bu
        last12, prev12 = self.months[-12:], self.months[-24:-12]
        r_now = sum(r["revenue"] for r in self.fin if r["bu_id"] == strong["bu_id"] and r["month"] in last12)
        r_prev = sum(r["revenue"] for r in self.fin if r["bu_id"] == strong["bu_id"] and r["month"] in prev12)
        strong_growth = 100 * (r_now / r_prev - 1)
        lt_up = 35  # planted increase (rounded lead times show 30-40%)
        self.signals = [
            {"signal_id": "SIG1", "severity": "medium", "layer": "supply chain", "entity_type": "supplier",
             "entity_id": sup["supplier_id"], "title": f"{sup['name']} lead times up {lt_up}%",
             "detail": f"Lead time {sup['baseline_lead_time_days']:.1f} → {sup['current_lead_time_days']:.1f} days over 3 months; on-time delivery 96% → 86%. "
                       f"{sup['dependency_pct']:.0f}% of {sup['category']} spend; it supports '{proc['name']}'. A qualified standby supplier exists.",
             "detected_days_ago": 11, "caused_by": None},
            {"signal_id": "SIG2", "severity": "high", "layer": "operations", "entity_type": "process",
             "entity_id": proc["process_id"], "title": f"{proc['name']} cycle time up 30%",
             "detail": f"{proc['target_cycle_hours']}h → {proc['current_cycle_hours']}h; backlog 1.6× normal; SLA attainment "
                       f"{proc['current_sla_attainment_pct'] + 7:.1f}% → {proc['current_sla_attainment_pct']:.1f}% (target {proc['sla_target_pct']}%).",
             "detected_days_ago": 8, "caused_by": "SIG1"},
            {"signal_id": "SIG3", "severity": "medium", "layer": "customers", "entity_type": "segment",
             "entity_id": seg["segment_id"], "title": f"Churn in {seg['name']} up from {seg['base_churn']:.1f}% to {seg['churn_monthly_pct']:.1f}% a month",
             "detail": f"NPS {seg['base_nps']:.0f} → {seg['nps']:.0f}; feedback mentions '{proc['name']}' delays. "
                       f"{seg['customers']:,} customers, {self.money(seg['annual_revenue'])} annual revenue.",
             "detected_days_ago": 5, "caused_by": "SIG2"},
            {"signal_id": "SIG4", "severity": "strength", "layer": "finance", "entity_type": "business_unit",
             "entity_id": strong["bu_id"], "title": f"{strong['name']} growing {strong_growth:.1f}% — ahead of its {strong['growth_target_pct']:.1f}% plan",
             "detail": f"{100 * strong['revenue_share']:.0f}% of revenue; gross margin on target. A unit to learn from and invest behind.",
             "detected_days_ago": 7, "caused_by": None},
            {"signal_id": "SIG5", "severity": "strength", "layer": "customers", "entity_type": "segment",
             "entity_id": loyal["segment_id"], "title": f"{loyal['name']}: NPS up to {loyal['nps']:.0f} and churn down to {loyal['churn_monthly_pct']:.2f}% a month",
             "detail": f"Best in two years (NPS was {loyal['base_nps']:.0f}, churn {loyal['base_churn']:.2f}%); {loyal['customers']:,} customers, "
                       f"{self.money(loyal['annual_revenue'])} annual revenue — the most loyal part of the base.",
             "detected_days_ago": 10, "caused_by": None},
            {"signal_id": "SIG6", "severity": "strength", "layer": "operations", "entity_type": "process",
             "entity_id": good_proc["process_id"], "title": f"{good_proc['name']} 14% faster, SLA at {good_proc['current_sla_attainment_pct']:.1f}%",
             "detail": f"{good_proc['target_cycle_hours']}h → {good_proc['current_cycle_hours']}h over six months, above its {good_proc['sla_target_pct']}% target — "
                       f"a playbook other processes could reuse.",
             "detected_days_ago": 12, "caused_by": None},
        ]
        spof_days = next(b["days_to_breach"] for b in self.tables["buffers"] if b["entity_id"] == self.spof["system_id"])
        renew = [a for a in self.affected if a["renewal_in_days"] <= 60]
        renew_acv = sum(a["annual_contract_value_base"] for a in renew)
        burn = sum(self.to_base(a["sla_penalty_per_hour"], a["currency"]) for a in self.affected)
        accrued = sum(self.to_base(a["sla_penalty_accrued"], a["currency"]) for a in self.affected)
        currencies = sorted({a["currency"] for a in self.affected})
        under = [st for st in self.tables["sites"] if st["region"] == self.growth["region"] and st["type"] == self.growth["site_type"]]
        util = sum(st["utilization_pct"] for st in under) / max(1, len(under))
        self.signals += [
            {"signal_id": "SIG7", "severity": "high", "layer": "customers", "entity_type": "accounts",
             "entity_id": ", ".join(a["account_id"] for a in renew),
             "title": f"{len(renew)} key accounts worth {self.money(renew_acv)} a year renew within 60 days — affected by {proc['name']} delays",
             "detail": f"{len(self.affected)} key accounts have work outside SLA in '{proc['name']}'; health scores 55-66 and churn risk 22-38% "
                       f"(the rest of the key accounts are healthy).",
             "detected_days_ago": 4, "caused_by": "SIG2"},
            {"signal_id": "SIG8", "severity": "medium", "layer": "finance", "entity_type": "accounts",
             "entity_id": ", ".join(a["account_id"] for a in self.affected),
             "title": f"SLA penalties accruing at {self.money(burn)} an hour across {len(self.affected)} contracts",
             "detail": f"{self.money(accrued)} accrued so far, in {', '.join(currencies)}; they stop once '{proc['name']}' is back within SLA.",
             "detected_days_ago": 6, "caused_by": "SIG2"},
            {"signal_id": "SIG9", "severity": "medium", "layer": "operations", "entity_type": "system",
             "entity_id": self.spof["system_id"],
             "title": f"{self.spof['name']} headroom at {self.spof['capacity_headroom_pct']:.0f}% — reaches the 5% floor in ~{spof_days:.0f} days",
             "detail": f"No failover yet; supports {self.spof['supports_processes']}. It slowed down at the last month-end peak (INC-288) — "
                       f"time to add capacity before the next one.",
             "detected_days_ago": 2, "caused_by": None},
            {"signal_id": "SIG10", "severity": "opportunity", "layer": "strategy", "entity_type": "region",
             "entity_id": self.growth["region"],
             "title": f"Spare capacity: {self.growth['site_type'].lower()}s in {self.growth['region']} at {util:.0f}% utilisation",
             "detail": f"Meanwhile '{self.growth['opportunity']}' is growing 18% a year in {self.growth['region']} with a high capability fit — "
                       f"a possible growth play using capacity we already pay for.",
             "detected_days_ago": 9, "caused_by": None},
        ]
        for s in self.signals:
            self.add("signals", s)
        self.add("risks", {"risk_id": f"RK{len(self.tables['risks']) + 1}",
                           "title": f"Dependency on {sup['name']} ({sup['dependency_pct']:.0f}% of {sup['category']})",
                           "category": "Supply chain", "likelihood": 3, "impact": 4, "owner": self.leaders["COO"],
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
            CREATE TABLE reports (report_id TEXT PRIMARY KEY, title TEXT, path TEXT, created_at TEXT, author TEXT);
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
            *[f"- **{b['name']}** — {100 * b['revenue_share']:.0f}% of revenue; products: {', '.join(b['products'])}" for b in self.bus],
            "",
            "People appear in the twin as roles only (e.g. Chief Operating Officer); key accounts as segment labels.",
            "",
            "## What is going well",
            *[f"- **{s['signal_id']} {s['title']}** — {s['detail']}" for s in self.signals if s["severity"] in ('strength',)],
            "",
            "## Risks to watch",
            *[f"- **{s['signal_id']} {s['title']}** — {s['detail']}" for s in self.signals if s["severity"] in ('high', 'medium')],
            "",
            "## Opportunities",
            *[f"- **{s['signal_id']} {s['title']}** — {s['detail']}" for s in self.signals if s["severity"] in ('opportunity',)],
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
