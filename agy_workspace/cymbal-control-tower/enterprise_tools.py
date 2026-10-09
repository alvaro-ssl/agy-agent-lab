"""Ready-to-use ADK function tools connecting Play 2 (`agents-cli`) to Cymbal Control Tower & Live FX APIs."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from database import fetch_all_incidents, fetch_incident_by_id, init_db, record_credit

init_db()


def get_active_incidents(vertical_filter: str = "") -> list[dict[str, Any]]:
    """Fetches active EMEA enterprise incidents from the Cymbal Control Tower database (with PII redacted).

    Args:
        vertical_filter: Optional vertical name (e.g., 'Retail', 'FinTech', 'Telco') to filter incidents.
    """
    rows = fetch_all_incidents()
    sanitized = []
    for r in rows:
        if vertical_filter and vertical_filter.lower() not in r["vertical"].lower():
            continue
        iban = r.get("customer_iban", "")
        masked_iban = f"{iban[:4]} **** **** {iban[-4:]}" if len(iban) >= 8 else "REDACTED"
        sanitized.append(
            {
                "incident_id": r["incident_id"],
                "account_name": r["account_name"],
                "vertical": r["vertical"],
                "sla_tier": r["sla_tier"],
                "summary": r["summary"],
                "severity": r["severity"],
                "downtime_mins": r["downtime_mins"],
                "penalty_rate_per_hr": r["penalty_rate_per_hr"],
                "billing_currency": r["billing_currency"],
                "masked_iban": masked_iban,
                "status": r["status"],
            }
        )
    return sanitized


def get_live_fx_rate(base_currency: str = "EUR", target_currency: str = "USD") -> dict[str, Any]:
    """Calls the free, no-key Frankfurter ECB REST API (from cszhu.dev/build-with-gemini) for live exchange rates.

    Args:
        base_currency: Three-letter ISO currency code (e.g., 'EUR', 'GBP', 'USD').
        target_currency: Three-letter ISO currency code to convert into.
    """
    base = base_currency.upper().strip()
    target = target_currency.upper().strip()
    if base == target:
        return {"base": base, "target": target, "rate": 1.0, "source": "identity"}
    url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rate = data.get("rates", {}).get(target, 1.0)
            return {"base": base, "target": target, "rate": rate, "date": data.get("date")}
    except Exception as exc:
        # Fallback rates if offline in conference venue Wi-Fi
        fallback = {("USD", "EUR"): 0.92, ("GBP", "EUR"): 1.17, ("EUR", "USD"): 1.09, ("EUR", "GBP"): 0.85}
        return {
            "base": base,
            "target": target,
            "rate": fallback.get((base, target), 1.0),
            "source": f"offline_fallback ({exc})",
        }


def issue_sla_remediation_credit(
    incident_id: str,
    amount_eur: float,
    reason: str,
    manager_approved: bool = False,
) -> dict[str, Any]:
    """Issues a goodwill or contractual SLA credit in EUR to an impacted enterprise customer.

    IMPORTANT EXECUTIVE GUARDRAIL:
    Any credit above €500.00 requires explicit human manager sign-off (`manager_approved=True`).

    Args:
        incident_id: The incident ID (e.g., 'INC-401').
        amount_eur: Credit amount in EUR.
        reason: Business justification for the credit.
        manager_approved: True only if a human executive explicitly approved > €500.
    """
    inc = fetch_incident_by_id(incident_id)
    if not inc:
        return {"status": "ERROR", "message": f"Incident {incident_id} not found."}

    if amount_eur > 500.0 and not manager_approved:
        return {
            "status": "PENDING_EXECUTIVE_APPROVAL",
            "incident_id": incident_id,
            "requested_amount_eur": amount_eur,
            "policy_limit_eur": 500.0,
            "message": (
                f"Guardrail triggered: €{amount_eur:.2f} exceeds the €500.00 autonomous limit. "
                "Ask the user for explicit manager approval before calling with manager_approved=True."
            ),
        }

    return record_credit(
        incident_id=incident_id,
        account_name=inc["account_name"],
        amount_eur=amount_eur,
        manager_approved=manager_approved,
        reason=reason,
    )


def _google_search_fallback(query: str) -> dict[str, Any] | None:
    """Uses Gemini Google Search grounding (or Google News RSS + Wikipedia API) when a website is not found or blocked."""
    import re
    import urllib.parse
    import xml.etree.ElementTree as ET

    # 1. Try Gemini Google Search Grounding via google.genai if credentials are available
    try:
        from google import genai
        from google.genai import types

        client = genai.Client()
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"Search Google for the company or website '{query}'. "
                "Return its official website URL, industry vertical, top 4 customer-facing digital products "
                "or services, and a concise 3-sentence operational summary."
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )
        if resp and resp.text:
            return {
                "query": query,
                "status": "OK_FALLBACK_GOOGLE_SEARCH",
                "source": "google_search_grounding (gemini-2.5-flash)",
                "title": f"{query} — Live Google Search Grounded Briefing",
                "top_headings": [
                    f"{query} Core Digital Products & Services",
                    "EMEA Operational & SLA Footprint",
                    "Live Google Search Grounding Summary",
                ],
                "content_excerpt": resp.text.strip()[:4000],
            }
    except Exception:
        pass

    # 2. Keyless Google News Search RSS + Wikipedia REST summary fallback (works without cloud auth)
    snippets: list[str] = []
    headings: list[str] = []
    try:
        q_encoded = urllib.parse.quote_plus(f"{query} company products digital")
        rss_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=en-GB&gl=GB&ceid=GB:en"
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            for item in root.findall(".//item")[:5]:
                t = (item.findtext("title") or "").strip()
                if t:
                    headings.append(t)
                    snippets.append(t)
    except Exception:
        pass

    try:
        slug = urllib.parse.quote(query.strip().replace("https://", "").replace("http://", "").replace("www.", "").split(".")[0].capitalize())
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            wdata = json.loads(resp.read().decode("utf-8", errors="ignore"))
            extract = wdata.get("extract", "")
            if extract:
                snippets.insert(0, extract)
    except Exception:
        pass

    if snippets:
        return {
            "query": query,
            "status": "OK_FALLBACK_GOOGLE_SEARCH",
            "source": "google_search_rss_and_knowledge_graph",
            "title": f"{query} — Google Search Fallback Briefing",
            "top_headings": headings[:6] or [f"{query} Digital Operations", f"{query} Enterprise Products"],
            "content_excerpt": " | ".join(snippets)[:4000],
        }
    return None


def fetch_company_website_briefing(company_url_or_name: str) -> dict[str, Any]:
    """Fetches live public webpage content from a company URL/domain, with automatic Google Search and offline fallbacks.

    Tier 1: Fetches live HTML (<title>, <h1>-<h3> headings, and clean text) directly from the company's website.
    Tier 2 (Google Search Fallback): If the user provides a company name without a URL, or if the website blocks
            bots/times out, automatically falls back to Google Search grounding / Google Search RSS.
    Tier 3 (Offline Venue Fallback): If conference Wi-Fi is unavailable, returns a deterministic executive profile
            so the workshop exercise never fails.

    Args:
        company_url_or_name: A company URL (e.g., 'https://www.siemens.com'), domain ('klarna.com'),
                             or company name ('Vodafone', 'Deutsche Telekom').
    """
    import re

    raw_input = company_url_or_name.strip()
    # Determine candidate URL if a company name or domain was given
    if raw_input.startswith(("http://", "https://")):
        candidate_url = raw_input
    elif "." in raw_input and " " not in raw_input:
        candidate_url = f"https://{raw_input}"
    else:
        slug = re.sub(r"[^a-z0-9]", "", raw_input.lower())
        candidate_url = f"https://www.{slug}.com" if slug else ""

    req_error = None
    if candidate_url:
        req = urllib.request.Request(
            candidate_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw_html = resp.read().decode("utf-8", errors="ignore")
                title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.I | re.S)
                title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else candidate_url
                cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
                headings = [
                    re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
                    for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", cleaned, flags=re.I | re.S)
                ]
                headings = [h for h in headings if h][:12]
                text = re.sub(r"<[^>]+>", " ", cleaned)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) >= 80:
                    return {
                        "url": candidate_url,
                        "status": "OK_LIVE_WEBSITE",
                        "source": "live_website_direct",
                        "title": title,
                        "top_headings": headings,
                        "content_excerpt": text[:4000],
                    }
                req_error = "Website returned minimal text (SPA or bot-challenge page)"
        except Exception as exc:
            req_error = str(exc)

    # Tier 2: Google Search Fallback (when no website is found or live URL fetch fails/blocks)
    search_res = _google_search_fallback(raw_input)
    if search_res is not None:
        search_res["attempted_url"] = candidate_url
        search_res["fallback_reason"] = req_error or "No website URL provided; resolved via Google Search"
        return search_res

    # Tier 3: Deterministic Offline Fallback so the exercise never fails on conference Wi-Fi
    clean_name = raw_input.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    return {
        "url": candidate_url or f"https://www.{clean_name.lower()}.com",
        "status": "OK_OFFLINE_FALLBACK",
        "source": f"deterministic_offline_fallback ({req_error or 'offline'})",
        "title": f"{clean_name} — Enterprise Digital & Operations Profile (Fallback)",
        "top_headings": [
            f"{clean_name} Core Digital Platform & Customer Portal",
            f"{clean_name} Real-Time Checkout / API Gateway Services",
            f"{clean_name} EMEA Cloud Infrastructure & SLA Commitments",
        ],
        "content_excerpt": (
            f"{clean_name} operates mission-critical customer-facing digital platforms, API gateways, and "
            "enterprise transaction services across EMEA. A P0 outage impacting primary digital channels "
            "carries a baseline contractual SLA penalty exposure of 45,000.00 EUR/hour with a 15% compounding "
            "hourly escalator, subject to the 500.00 EUR autonomous remediation credit guardrail."
        ),
    }


def get_digital_twin_state(
    layer: str = "all",
    abstraction_level: str = "strategic",
) -> dict[str, Any]:
    """Queries the 6-Layer Digital Twin of the Organization (State Master Data + Real-Time Flow Telemetry).

    Layers modeled:
      1. Organizational Structure & Human Capital (`org_human_capital`)
      2. Business Processes & Workflows (`workflows`)
      3. Financial & Economic Dynamics (`finance`)
      4. Customers, Market & Demand (`customers_demand`)
      5. Physical & Digital Infrastructure (`infrastructure`)
      6. Governance, Risk & Policy Constraints (`governance`)

    Args:
        layer: 'all', or one of 'org_human_capital', 'workflows', 'finance',
               'customers_demand', 'infrastructure', 'governance'.
        abstraction_level: 'strategic' (C-suite aggregated KPIs, P&L, capacity, risk)
                           or 'operational' (includes granular ERP/CRM/ServiceNow process event logs & queues).
    """
    from dto_digital_twin import query_digital_twin_snapshot

    return query_digital_twin_snapshot(layer=layer, abstraction_level=abstraction_level)


def simulate_dto_causal_shock(
    shock_type: str = "infra_and_supply_shock",
    target_hub_or_asset: str = "Frankfurt-K8s-Payment-Core",
    duration_hours: int = 4,
    workforce_capacity_delta_pct: float = -15.0,
    supplier_delay_days: int = 2,
) -> dict[str, Any]:
    """Runs a Causal Digital Twin simulation propagating an operational/supply shock across all 6 organizational layers.

    Propagates:
      Layer 5 (Asset Outage / Supplier Lead-Time Shock)
      -> Layer 2 (Workflow Queue Backlog, Cycle Time & Rework)
      -> Layer 1 (Human Capital Utilization Surge & Overtime OPEX)
      -> Layer 4 (Customer Funnel Drop, Compounding SLAs in EUR & Churn Risk)
      -> Layer 3 (P&L Revenue Burn, EBITDA Erosion & Working Capital Lockup)
      -> Layer 6 (Governance, EU Working Time 90% Cap, DORA 120m RTO & €500 Spend Guardrail)

    Args:
        shock_type: Description of the scenario (e.g., 'infra_and_supply_shock', 'cloud_outage', 'supplier_delay').
        target_hub_or_asset: Primary asset or hub impacted (e.g., 'Frankfurt-K8s-Payment-Core', 'Rotterdam-Automated-DC-01').
        duration_hours: Outage or disruption duration in hours (default 4).
        workforce_capacity_delta_pct: Percentage change in available FTE capacity (e.g., -15.0 for a 15% staffing shortage).
        supplier_delay_days: Days of upstream supply chain / replenishment delay (default 2).
    """
    from dto_digital_twin import simulate_dto_causal_shock as _run_dto_shock

    usd_eur = float(get_live_fx_rate("USD", "EUR").get("rate", 0.92))
    gbp_eur = float(get_live_fx_rate("GBP", "EUR").get("rate", 1.17))
    return _run_dto_shock(
        shock_type=shock_type,
        target_hub_or_asset=target_hub_or_asset,
        duration_hours=duration_hours,
        workforce_capacity_delta_pct=workforce_capacity_delta_pct,
        supplier_delay_days=supplier_delay_days,
        fx_rates_to_eur={"EUR": 1.0, "USD": usd_eur, "GBP": gbp_eur},
    )


