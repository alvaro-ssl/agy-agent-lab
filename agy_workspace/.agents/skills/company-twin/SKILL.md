---
name: company-twin
description: >-
  Reshapes the synthetic digital twin in company-twin/ into a real company. Use when the user invokes
  /company-twin <company name or website>, or asks to make the digital twin look like a company.
---

# Make the digital twin look like a company (`/company-twin <company>`)

The user gives only a company name or website. Do the rest without asking more questions.

1. **Research** the company with **one** web search (two at most): industry, headquarters, currency, annual
   revenue, employees, main regions, business units and their main products or services, current strategic
   priorities. If a search fails or is slow, carry on with what you know and say so — never wait on it.
2. **Rewrite `company-twin/company_profile.yaml`**, keeping its structure:
   - `industry` must be one of the values listed in the file — pick the closest and say which you chose;
   - `annual_revenue_m` in millions of the company's reporting currency; rounded public figures only;
   - region and business-unit `revenue_share` values each add up to about 1.0;
   - 3–4 business units with 2–3 `products` each; 3 `strategic_priorities`;
   - set realistic `revenue_growth_target_pct` and `ebitda_margin_target_pct` for the company;
   - never write people's names anywhere — the twin uses roles (e.g. Chief Operating Officer) and segment labels
     for key accounts.
3. **Generate the twin:** `.venv/bin/python company-twin/generate_twin.py`
4. **Start the Company Twin** if nothing is listening on port 8090:
   `.venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090` (in the background).
5. **Open it — no screenshot:** run `open http://localhost:8090` (macOS; `xdg-open` on Linux) and print the URL
   as a clickable link.
6. **Reply in five lines or fewer**, balanced and constructive: what the company looks like in the twin
   (industry, scale, business units), one thing going well, the two biggest risks to watch and the opportunity
   from `company-twin/data/twin_summary.md`, then the link http://localhost:8090. Mention that the data is
   synthetic and only shaped like the real company.
