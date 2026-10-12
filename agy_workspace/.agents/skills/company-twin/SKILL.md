---
name: company-twin
description: >-
  Reshapes the synthetic digital twin in company-twin/ into a real company. Use when the user invokes
  /company-twin <company name or website>, or asks to make the digital twin look like a company.
---

# Make the digital twin look like a company (`/company-twin <company>`)

The user gives only a company name or website. Do the rest without asking more questions.

1. **Research** the company from its website and Google Search (use what you know if you are offline, and say
   so): industry, headquarters, currency, annual revenue, employees, main regions, business units and their main
   products or services, current strategic priorities.
2. **Rewrite `company-twin/company_profile.yaml`**, keeping its structure:
   - `industry` must be one of the values listed in the file — pick the closest and say which you chose;
   - `annual_revenue_m` in millions of the company's reporting currency; rounded public figures only;
   - region and business-unit `revenue_share` values each add up to about 1.0;
   - 3–4 business units with 2–3 `products` each; 3 `strategic_priorities`;
   - set realistic `revenue_growth_target_pct` and `ebitda_margin_target_pct` for the company;
   - never write real people's names anywhere — leadership names are generated.
3. **Generate the twin:** `.venv/bin/python company-twin/generate_twin.py`
4. **Start the Company Twin** if nothing is listening on port 8090:
   `.venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090` (in the background).
5. **Show it:** take a screenshot of http://localhost:8090 with the `browser` skill (or ask the user to open it).
6. **Reply in five lines or fewer:** what the company looks like in the twin (industry, scale, business units),
   and the three most severe signals from `company-twin/data/twin_summary.md`. Mention that the data is
   synthetic and only shaped like the real company.
