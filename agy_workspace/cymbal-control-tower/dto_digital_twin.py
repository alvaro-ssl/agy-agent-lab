"""6-Layer Digital Twin of an Organization (DTO) — Schema, Seed Data & Causal Propagation Engine.

Models both Structural Baseline (State / Master Data) and Real-Time Telemetry (Flow Data) across:
  Layer 1: Organizational Structure & Human Capital (`dto_org_units`)
  Layer 2: Business Processes & Workflows (`dto_workflows`, `dto_process_events`)
  Layer 3: Financial & Economic Dynamics (`dto_financial_accounts`)
  Layer 4: Customers, Market & Demand (`dto_customer_cohorts`)
  Layer 5: Physical & Digital Infrastructure (`dto_infra_assets`)
  Layer 6: Governance, Risk & Policy Constraints (`dto_governance_policies`)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "cymbal_ops.db"

# Layer 1: Organizational Structure & Human Capital (State + Flow)
SEED_ORG_UNITS = [
    (
        "ORG-DE-FSI",
        "Frankfurt FinTech & Payments Core",
        "EMEA-Central (Frankfurt)",
        "CTO -> VP Cloud & Payments",
        42,
        0.18,
        "SEPA_Clearing_L3, K8s_SRE, DORA_Compliance",
        94.5,
        80.0,
        14.8,
        6.5,
        115.0,
        "SATURATED_WARNING",
    ),
    (
        "ORG-SE-RET",
        "Stockholm Omnichannel & Retail Ops",
        "EMEA-Nordics (Stockholm)",
        "COO -> VP Retail Operations",
        65,
        0.25,
        "SAP_SCM_Architect, WMS_Integration, Order_Orchestration",
        88.2,
        78.0,
        11.2,
        4.0,
        95.0,
        "HIGH_LOAD",
    ),
    (
        "ORG-UK-TEL",
        "London Telco & Energy Grid NOC",
        "EMEA-West (London)",
        "CTO -> VP Network Reliability",
        38,
        0.12,
        "5G_Core_Slicing, Telemetry_Kafka, SCADA_Security",
        82.0,
        75.0,
        9.5,
        5.5,
        110.0,
        "NOMINAL",
    ),
    (
        "ORG-ES-LOG",
        "Madrid Iberia Fulfillment & Reverse Logistics",
        "EMEA-South (Madrid)",
        "COO -> VP Supply Chain",
        80,
        0.32,
        "Warehouse_Robotics, Carrier_EDI, Customs_Clearance",
        79.4,
        75.0,
        16.5,
        3.0,
        68.0,
        "NOMINAL",
    ),
]

# Layer 2A: Business Processes & Workflows Master (State)
SEED_WORKFLOWS = [
    (
        "WF-SEPA-01",
        "SEPA-Instant-Settlement",
        "ORG-DE-FSI",
        "Stripe_SEPA -> SAP_FICO -> ServiceNow",
        12.0,
        54.0,
        42.0,
        18.5,
        "If webhook_latency > 500ms or settlement_val > 500 EUR -> route to L3_SRE & VP_Finance gate",
        "BOTTLENECK_CRITICAL",
    ),
    (
        "WF-OTC-02",
        "Omnichannel-Order-to-Cash",
        "ORG-SE-RET",
        "Salesforce_CRM -> Nordic_WMS -> SAP_ERP",
        25.0,
        88.0,
        63.0,
        14.2,
        "If SKU_buffer < 2.0 days -> trigger emergency split-shipment & customer SLA alert",
        "BOTTLENECK_CRITICAL",
    ),
    (
        "WF-5G-03",
        "5G-Enterprise-Slice-Provisioning",
        "ORG-UK-TEL",
        "ServiceNow -> Telco_Core_API -> Prometheus",
        30.0,
        47.0,
        17.0,
        6.0,
        "If packet_loss > 0.5% -> auto-failover to secondary Frankfurt edge node",
        "DEGRADED",
    ),
    (
        "WF-REV-04",
        "Iberia-Reverse-Logistics-Returns",
        "ORG-ES-LOG",
        "Shopify_Plus -> Carrier_EDI -> SAP_WM",
        45.0,
        58.0,
        13.0,
        4.5,
        "Standard automated RMA label issue if order < 500 EUR",
        "NOMINAL",
    ),
]

# Layer 2B: Granular Process Event Logs for Process Mining (Flow)
SEED_PROCESS_EVENTS = [
    (
        "EVT-9001",
        "CASE-FSI-8821",
        "WF-SEPA-01",
        "SEPA_Webhook_Signature_Verify",
        "Stripe_SEPA",
        "ORG-DE-FSI",
        28.5,
        1,
        "Connection pool saturation on Frankfurt-K8s-Payment-Core",
    ),
    (
        "EVT-9002",
        "CASE-FSI-8821",
        "WF-SEPA-01",
        "DORA_Compliance_Handoff",
        "ServiceNow",
        "ORG-DE-FSI",
        13.5,
        1,
        "Manual L3 SRE handoff queue delay (team at 94.5% utilization)",
    ),
    (
        "EVT-9003",
        "CASE-RET-4410",
        "WF-OTC-02",
        "Inventory_Reservation_Sync",
        "Nordic_WMS",
        "ORG-SE-RET",
        49.0,
        1,
        "DB lock contention during DE/SE store stock sync",
    ),
    (
        "EVT-9004",
        "CASE-RET-4410",
        "WF-OTC-02",
        "Split_Shipment_Allocation",
        "SAP_ERP",
        "ORG-SE-RET",
        14.0,
        0,
        "Rotterdam DC buffer stock below 1.5 days triggered re-routing",
    ),
    (
        "EVT-9005",
        "CASE-TEL-3109",
        "WF-5G-03",
        "Telemetry_Slice_Health_Check",
        "Prometheus",
        "ORG-UK-TEL",
        17.0,
        0,
        "Frankfurt core edge router packet drop",
    ),
]

# Layer 3: Financial & Economic Dynamics (State + Flow)
SEED_FINANCIAL_ACCOUNTS = [
    (
        "FIN-CC-FSI",
        "FinTech & Instant Payments P&L",
        "ORG-DE-FSI",
        48500000.0,
        74.5,
        25.5,
        1850.0,
        24500.0,
        28,
        1200.0,
        42000.0,
        "GBP",
    ),
    (
        "FIN-CC-RET",
        "Omnichannel Retail & E-Commerce P&L",
        "ORG-SE-RET",
        62000000.0,
        52.0,
        48.0,
        420.0,
        4800.0,
        42,
        6800.0,
        35000.0,
        "USD",
    ),
    (
        "FIN-CC-TEL",
        "Enterprise Telco & Grid P&L",
        "ORG-UK-TEL",
        39000000.0,
        68.0,
        32.0,
        3100.0,
        38000.0,
        35,
        900.0,
        18000.0,
        "EUR",
    ),
    (
        "FIN-CC-LOG",
        "Iberia Supply Chain & Fulfillment Cost Center",
        "ORG-ES-LOG",
        19500000.0,
        41.0,
        59.0,
        190.0,
        1950.0,
        51,
        4900.0,
        8500.0,
        "EUR",
    ),
]

# Layer 4: Customers, Market & Demand (State + Flow)
SEED_CUSTOMER_COHORTS = [
    (
        "CUST-NORDIC",
        "NordicHome Omnichannel",
        "Retail & E-Commerce",
        "Platinum",
        14500000.0,
        "USD",
        1200.0,
        15.0,
        420,
        3.8,
        2.4,
        14.5,
        -18,
        "SE45 **** **** 7466",
        "INC-401",
    ),
    (
        "CUST-NEOBANK",
        "NeoBank26 Europe",
        "FinTech & FSI",
        "Platinum",
        19800000.0,
        "GBP",
        2500.0,
        20.0,
        1850,
        6.2,
        4.1,
        19.0,
        -24,
        "DE89 **** **** 3000",
        "INC-402",
    ),
    (
        "CUST-EUROGRID",
        "EuroGrid & Telco",
        "Telco & Energy",
        "Gold",
        11200000.0,
        "EUR",
        450.0,
        10.0,
        95,
        2.9,
        2.5,
        7.8,
        -9,
        "GB29 **** **** 6819",
        "INC-403",
    ),
    (
        "CUST-LUXFASH",
        "LuxFashion Marketplace",
        "Retail & E-Commerce",
        "Silver",
        5400000.0,
        "EUR",
        75.0,
        5.0,
        310,
        3.1,
        2.9,
        5.2,
        -4,
        "PT50 **** **** 0154",
        "INC-404",
    ),
]

# Layer 5: Physical & Digital Infrastructure (Asset & Supply Chain Layer)
SEED_INFRA_ASSETS = [
    (
        "ASSET-DIG-01",
        "Frankfurt-K8s-Payment-Core",
        "DIGITAL_IT_CLUSTER",
        "ORG-DE-FSI",
        "WF-SEPA-01",
        97.8,
        1420,
        720,
        94.0,
        0.0,
        0.0,
        0,
        "DEGRADED_LATENCY_SPIKE",
    ),
    (
        "ASSET-DIG-02",
        "Nordic-WMS-Sync-API",
        "DIGITAL_IT_API",
        "ORG-SE-RET",
        "WF-OTC-02",
        96.4,
        1180,
        650,
        91.5,
        0.0,
        0.0,
        0,
        "DEGRADED_LOCK_CONTENTION",
    ),
    (
        "ASSET-PHY-03",
        "Rotterdam-Automated-DC-01",
        "PHYSICAL_WAREHOUSE_AND_SCM",
        "ORG-SE-RET",
        "WF-OTC-02",
        99.1,
        45,
        1400,
        89.0,
        1.2,
        5.0,
        36,
        "LOW_BUFFER_STOCK_WARNING",
    ),
    (
        "ASSET-PHY-04",
        "Madrid-Iberia-Fulfillment-Hub",
        "PHYSICAL_WAREHOUSE_AND_FLEET",
        "ORG-ES-LOG",
        "WF-REV-04",
        99.6,
        32,
        1800,
        76.0,
        4.8,
        4.0,
        0,
        "HEALTHY",
    ),
]

# Layer 6: Governance, Risk & Policy Constraints
SEED_GOVERNANCE_POLICIES = [
    (
        "FIN-CAP-500",
        "Autonomous SLA Credit & OPEX Cap",
        "FINANCIAL_RISK",
        "500.00 EUR",
        "Any customer SLA credit or emergency OPEX reallocation > 500.00 EUR requires explicit manager_approved=True (VP Finance / CFO sign-off).",
        "ACTIVE_ENFORCED",
    ),
    (
        "EU-WTD-90",
        "EU Working Time & Burnout Ceiling",
        "LABOR_COMPLIANCE",
        "90.0% Utilization",
        "Any org unit exceeding 90.0% shift utilization must trigger contractor surge allocation or cross-hub load balancing.",
        "BREACH_WARNING (ORG-DE-FSI at 94.5%)",
    ),
    (
        "DORA-RTO-120",
        "EU DORA FinTech Operational Resilience",
        "REGULATORY_LEGAL",
        "120 Mins Max Downtime",
        "P0 FinTech payment disruptions exceeding 120 minutes require mandatory BaFin/ECB incident notification.",
        "AT_RISK (INC-402 at 65m)",
    ),
    (
        "GDPR-PII-MASK",
        "GDPR Article 32 PII Redaction",
        "DATA_SOVEREIGNTY",
        "Zero Raw IBAN/Email",
        "All customer IBANs and personal emails must be masked across API payloads, logs, and Digital Twin simulations.",
        "ACTIVE_ENFORCED",
    ),
    (
        "SCM-BUFFER-3D",
        "Strategic Supply Chain Buffer Floor",
        "CONTRACTUAL_SCM",
        "3.0 Days Buffer Stock",
        "Fulfillment centers falling below 3.0 days of SKU buffer stock trigger expedited supplier replenishment.",
        "BREACH_WARNING (Rotterdam-DC at 1.2d)",
    ),
]


def init_dto_tables(conn: sqlite3.Connection) -> None:
    """Creates and seeds the 6 Digital Twin of an Organization (DTO) layers inside cymbal_ops.db."""
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_org_units (
            unit_id TEXT PRIMARY KEY,
            unit_name TEXT NOT NULL,
            region_hub TEXT NOT NULL,
            reporting_line TEXT NOT NULL,
            fte_count INTEGER NOT NULL,
            contractor_ratio REAL NOT NULL,
            core_skills TEXT NOT NULL,
            actual_utilization_pct REAL NOT NULL,
            planned_utilization_pct REAL NOT NULL,
            annual_attrition_pct REAL NOT NULL,
            ramp_up_weeks REAL NOT NULL,
            hourly_cost_eur REAL NOT NULL,
            capacity_status TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_workflows (
            workflow_id TEXT PRIMARY KEY,
            workflow_name TEXT NOT NULL,
            owner_unit_id TEXT NOT NULL,
            system_path TEXT NOT NULL,
            target_cycle_mins REAL NOT NULL,
            actual_cycle_mins REAL NOT NULL,
            avg_queue_wait_mins REAL NOT NULL,
            rework_freq_pct REAL NOT NULL,
            decision_branch_rule TEXT NOT NULL,
            workflow_status TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_process_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            activity_name TEXT NOT NULL,
            system_source TEXT NOT NULL,
            org_unit_id TEXT NOT NULL,
            wait_time_mins REAL NOT NULL,
            rework_flag INTEGER NOT NULL,
            diagnostic_note TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_financial_accounts (
            cost_center_id TEXT PRIMARY KEY,
            pnl_name TEXT NOT NULL,
            org_unit_id TEXT NOT NULL,
            annual_revenue_eur REAL NOT NULL,
            gross_margin_pct REAL NOT NULL,
            cogs_pct REAL NOT NULL,
            cac_eur REAL NOT NULL,
            ltv_eur REAL NOT NULL,
            ar_aging_days INTEGER NOT NULL,
            daily_inventory_carry_eur REAL NOT NULL,
            hourly_revenue_at_risk_eur REAL NOT NULL,
            primary_billing_currency TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_customer_cohorts (
            cohort_id TEXT PRIMARY KEY,
            account_name TEXT NOT NULL,
            vertical TEXT NOT NULL,
            sla_tier TEXT NOT NULL,
            arr_eur REAL NOT NULL,
            billing_currency TEXT NOT NULL,
            base_penalty_per_hr REAL NOT NULL,
            compounding_escalator_pct REAL NOT NULL,
            hourly_order_volume INTEGER NOT NULL,
            baseline_conversion_pct REAL NOT NULL,
            live_conversion_pct REAL NOT NULL,
            churn_risk_pct REAL NOT NULL,
            nps_delta INTEGER NOT NULL,
            masked_iban TEXT NOT NULL,
            active_incident_id TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_infra_assets (
            asset_id TEXT PRIMARY KEY,
            asset_name TEXT NOT NULL,
            asset_category TEXT NOT NULL,
            org_unit_id TEXT NOT NULL,
            linked_workflow_id TEXT NOT NULL,
            uptime_pct REAL NOT NULL,
            p99_latency_ms INTEGER NOT NULL,
            mtbf_hours INTEGER NOT NULL,
            capacity_utilization_pct REAL NOT NULL,
            sku_buffer_days REAL NOT NULL,
            target_buffer_days REAL NOT NULL,
            supplier_delay_hours INTEGER NOT NULL,
            health_status TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dto_governance_policies (
            policy_id TEXT PRIMARY KEY,
            policy_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            threshold_limit TEXT NOT NULL,
            enforcement_rule TEXT NOT NULL,
            live_compliance_status TEXT NOT NULL
        )
        """
    )

    cur.execute("SELECT COUNT(*) FROM dto_org_units")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO dto_org_units VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_ORG_UNITS,
        )
        cur.executemany(
            "INSERT INTO dto_workflows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_WORKFLOWS,
        )
        cur.executemany(
            "INSERT INTO dto_process_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_PROCESS_EVENTS,
        )
        cur.executemany(
            "INSERT INTO dto_financial_accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_FINANCIAL_ACCOUNTS,
        )
        cur.executemany(
            "INSERT INTO dto_customer_cohorts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_CUSTOMER_COHORTS,
        )
        cur.executemany(
            "INSERT INTO dto_infra_assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SEED_INFRA_ASSETS,
        )
        cur.executemany(
            "INSERT INTO dto_governance_policies VALUES (?, ?, ?, ?, ?, ?)",
            SEED_GOVERNANCE_POLICIES,
        )


def _fetch_table(table_name: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name}")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def query_digital_twin_snapshot(
    layer: str = "all",
    abstraction_level: str = "strategic",
) -> dict[str, Any]:
    """Queries the 6-Layer Digital Twin of the Organization (State Master Data + Real-Time Flow Telemetry).

    Args:
        layer: 'all', or one of 'org_human_capital', 'workflows', 'finance',
               'customers_demand', 'infrastructure', 'governance'.
        abstraction_level: 'strategic' (aggregated C-suite view for What-If planning)
                           or 'operational' (includes granular ERP/CRM/ServiceNow process event logs & queues).
    """
    layer_key = (layer or "all").lower().strip()
    level = (abstraction_level or "strategic").lower().strip()

    org_units = _fetch_table("dto_org_units")
    workflows = _fetch_table("dto_workflows")
    events = _fetch_table("dto_process_events")
    finance = _fetch_table("dto_financial_accounts")
    customers = _fetch_table("dto_customer_cohorts")
    assets = _fetch_table("dto_infra_assets")
    policies = _fetch_table("dto_governance_policies")

    layers_data: dict[str, Any] = {
        "1_org_and_human_capital": {
            "summary": {
                "total_emea_ftes": sum(u["fte_count"] for u in org_units),
                "saturated_hubs_over_90pct": [
                    u["unit_name"] for u in org_units if u["actual_utilization_pct"] > 90.0
                ],
                "avg_utilization_pct": round(
                    sum(u["actual_utilization_pct"] for u in org_units) / len(org_units), 1
                ),
            },
            "hubs": org_units,
        },
        "2_business_processes_and_workflows": {
            "summary": {
                "critical_bottlenecks": [
                    w["workflow_name"]
                    for w in workflows
                    if "BOTTLENECK" in w["workflow_status"]
                ],
                "max_queue_wait_mins": max(w["avg_queue_wait_mins"] for w in workflows),
            },
            "workflows": workflows,
            **(
                {"granular_process_mining_events": events}
                if level == "operational"
                else {}
            ),
        },
        "3_financial_and_economic_dynamics": {
            "summary": {
                "total_annual_revenue_eur": sum(f["annual_revenue_eur"] for f in finance),
                "total_hourly_revenue_at_risk_eur": sum(
                    f["hourly_revenue_at_risk_eur"] for f in finance
                ),
                "daily_inventory_carrying_cost_eur": sum(
                    f["daily_inventory_carry_eur"] for f in finance
                ),
            },
            "cost_centers_and_pnl": finance,
        },
        "4_customers_market_and_demand": {
            "summary": {
                "total_enterprise_arr_eur": sum(c["arr_eur"] for c in customers),
                "cohorts_with_conversion_drop": [
                    {
                        "account": c["account_name"],
                        "baseline_conv_pct": c["baseline_conversion_pct"],
                        "live_conv_pct": c["live_conversion_pct"],
                        "churn_risk_pct": c["churn_risk_pct"],
                    }
                    for c in customers
                    if c["live_conversion_pct"] < c["baseline_conversion_pct"]
                ],
            },
            "customer_cohorts": customers,
        },
        "5_physical_and_digital_infrastructure": {
            "summary": {
                "degraded_assets": [
                    a["asset_name"] for a in assets if a["health_status"] != "HEALTHY"
                ],
                "lowest_sku_buffer_days": min(
                    a["sku_buffer_days"] for a in assets if a["sku_buffer_days"] > 0
                ),
            },
            "assets_and_supply_chain": assets,
        },
        "6_governance_risk_and_policy_constraints": {
            "active_policies": policies,
            "active_breaches_or_warnings": [
                p for p in policies if "WARNING" in p["live_compliance_status"] or "RISK" in p["live_compliance_status"]
            ],
        },
    }

    if layer_key != "all":
        matched = {k: v for k, v in layers_data.items() if layer_key in k}
        if matched:
            return {"abstraction_level": level, "selected_layers": matched}

    return {
        "digital_twin_organization": "Cymbal EMEA Enterprise Operations (6-Layer DTO)",
        "abstraction_level": level,
        "layers": layers_data,
    }


def simulate_dto_causal_shock(
    shock_type: str = "infra_and_supply_shock",
    target_hub_or_asset: str = "Frankfurt-K8s-Payment-Core",
    duration_hours: int = 4,
    workforce_capacity_delta_pct: float = -15.0,
    supplier_delay_days: int = 2,
    fx_rates_to_eur: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Causal Digital Twin simulation propagating an operational or market shock across all 6 organizational layers.

    Causal Chain Modeled:
      Layer 5 (Asset Outage / Supplier Lead-Time Shock)
        --> Layer 2 (Workflow Queue Backlog, Cycle Time & Rework Escalation)
        --> Layer 1 (Human Capital Utilization Surge, Overtime & Ramp-Up Friction)
        --> Layer 4 (Customer Conversion Drop, Compounding SLA Penalties & Churn Risk)
        --> Layer 3 (P&L Revenue Burn, EBITDA Erosion, Working Capital & Multi-FX Impact)
        --> Layer 6 (Governance, EU Labor, DORA & €500 Autonomous Spend Guardrail Evaluation)
    """
    fx = fx_rates_to_eur or {"EUR": 1.0, "USD": 0.92, "GBP": 1.17}
    hours = max(1, int(duration_hours))
    supply_days = max(0, int(supplier_delay_days))

    org_units = _fetch_table("dto_org_units")
    workflows = _fetch_table("dto_workflows")
    finance = _fetch_table("dto_financial_accounts")
    customers = _fetch_table("dto_customer_cohorts")
    assets = _fetch_table("dto_infra_assets")

    # 1. Layer 5 -> Layer 2 Causal Propagation (Infrastructure & Supply -> Workflow Queues)
    capacity_loss_factor = max(0.0, -float(workforce_capacity_delta_pct) / 100.0)
    queue_multiplier = 1.0 + (0.28 * hours) + (0.45 * capacity_loss_factor) + (0.15 * supply_days)

    workflow_impacts = []
    for w in workflows:
        projected_queue_mins = round(w["avg_queue_wait_mins"] * queue_multiplier, 1)
        projected_rework_pct = round(min(45.0, w["rework_freq_pct"] * (1.0 + 0.12 * hours)), 1)
        workflow_impacts.append(
            {
                "workflow": w["workflow_name"],
                "baseline_cycle_mins": w["target_cycle_mins"],
                "projected_cycle_mins": round(w["target_cycle_mins"] + projected_queue_mins, 1),
                "projected_queue_wait_mins": projected_queue_mins,
                "projected_rework_pct": projected_rework_pct,
            }
        )

    # 2. Layer 2 -> Layer 1 Causal Propagation (Workflow Backlog -> Workforce Utilization & Overtime)
    workforce_impacts = []
    total_overtime_cost_eur = 0.0
    labor_breaches = []
    for u in org_units:
        new_util = round(
            min(100.0, u["actual_utilization_pct"] * (1.0 + capacity_loss_factor * 0.6 + 0.025 * hours)),
            1,
        )
        overtime_hrs = round(u["fte_count"] * hours * max(0.0, (new_util - 80.0) / 100.0), 1)
        overtime_eur = round(overtime_hrs * u["hourly_cost_eur"] * 1.5, 2)
        total_overtime_cost_eur += overtime_eur
        if new_util > 90.0:
            labor_breaches.append(f"{u['unit_name']} ({new_util}% > 90% EU-WTD-90 limit)")
        workforce_impacts.append(
            {
                "unit_name": u["unit_name"],
                "baseline_utilization_pct": u["actual_utilization_pct"],
                "projected_utilization_pct": new_util,
                "emergency_overtime_hours": overtime_hrs,
                "overtime_opex_eur": overtime_eur,
            }
        )

    # 3. Layer 1 & 2 -> Layer 4 Causal Propagation (Customer Funnel, Compounding SLAs & Churn)
    customer_impacts = []
    total_sla_penalty_eur = 0.0
    for c in customers:
        rate_to_eur = float(fx.get(c["billing_currency"], 1.0))
        base_hr_eur = float(c["base_penalty_per_hr"]) * rate_to_eur
        escalator = 1.0 + (float(c["compounding_escalator_pct"]) / 100.0)
        compounded_penalty_eur = sum(base_hr_eur * (escalator**h) for h in range(1, hours + 1))
        total_sla_penalty_eur += compounded_penalty_eur

        projected_churn_pct = round(
            min(35.0, c["churn_risk_pct"] + (1.8 * hours) + (1.2 * supply_days)), 1
        )
        arr_at_risk_eur = round(c["arr_eur"] * (projected_churn_pct / 100.0), 2)
        customer_impacts.append(
            {
                "account_name": c["account_name"],
                "vertical": c["vertical"],
                "billing_currency": c["billing_currency"],
                "compounded_sla_penalty_eur": round(compounded_penalty_eur, 2),
                "projected_churn_risk_pct": projected_churn_pct,
                "arr_at_risk_eur": arr_at_risk_eur,
            }
        )

    # 4. Layer 4 & 5 -> Layer 3 Causal Propagation (Financial P&L, Working Capital & Liquidity)
    hourly_rev_risk = sum(f["hourly_revenue_at_risk_eur"] for f in finance)
    direct_revenue_loss_eur = round(hourly_rev_risk * hours * (1.0 + 0.1 * supply_days), 2)
    working_capital_lockup_eur = round(
        sum(f["daily_inventory_carry_eur"] for f in finance) * max(1, supply_days) * 3.5, 2
    )
    total_ebitda_impact_eur = round(
        direct_revenue_loss_eur + total_sla_penalty_eur + total_overtime_cost_eur, 2
    )

    # 5. Layer 6 Governance & Boundary Constraints Evaluation
    dora_breach = hours * 60 + 65 > 120
    scm_buffer_breach = any(
        (a["sku_buffer_days"] - 0.4 * supply_days) < 3.0
        for a in assets
        if a["sku_buffer_days"] > 0
    )

    return {
        "simulation_parameters": {
            "shock_type": shock_type,
            "target_hub_or_asset": target_hub_or_asset,
            "duration_hours": hours,
            "workforce_capacity_delta_pct": workforce_capacity_delta_pct,
            "supplier_delay_days": supply_days,
        },
        "causal_propagation_results": {
            "layer_5_infra_and_supply_shock": {
                "target_asset": target_hub_or_asset,
                "rotterdam_dc_projected_buffer_days": round(max(0.0, 1.2 - 0.4 * supply_days), 2),
                "supply_chain_stockout_triggered": (1.2 - 0.4 * supply_days) <= 0.5,
            },
            "layer_2_workflow_bottlenecks": workflow_impacts,
            "layer_1_workforce_and_human_capital": {
                "total_emergency_overtime_opex_eur": round(total_overtime_cost_eur, 2),
                "hub_utilization_projections": workforce_impacts,
            },
            "layer_4_customer_demand_and_slas": {
                "total_compounded_sla_penalties_eur": round(total_sla_penalty_eur, 2),
                "cohort_impacts": customer_impacts,
            },
            "layer_3_financial_pnl_and_liquidity": {
                "direct_revenue_loss_eur": direct_revenue_loss_eur,
                "total_sla_penalties_eur": round(total_sla_penalty_eur, 2),
                "overtime_opex_burn_eur": round(total_overtime_cost_eur, 2),
                "total_ebitda_erosion_eur": total_ebitda_impact_eur,
                "working_capital_liquidity_lockup_eur": working_capital_lockup_eur,
            },
            "layer_6_governance_and_policy_triggers": {
                "FIN_CAP_500_autonomous_credit_blocked": total_sla_penalty_eur > 500.0,
                "required_financial_approver": (
                    "CFO_AND_VP_FINANCE" if total_ebitda_impact_eur > 5000.0 else "VP_OPERATIONS"
                ),
                "EU_WTD_90_labor_ceiling_breaches": labor_breaches,
                "DORA_RTO_120_regulator_filing_required": dora_breach,
                "SCM_BUFFER_3D_expedited_freight_required": scm_buffer_breach,
            },
        },
    }
