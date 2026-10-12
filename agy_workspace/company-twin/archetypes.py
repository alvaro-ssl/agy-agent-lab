"""Industry archetypes for the company digital twin.

An archetype gives the generator the *shape* of a company in an industry: its customer segments, core
processes, suppliers, sites, regulations, risks and seasonality. `company_profile.yaml` picks one archetype
and overrides names and scale with the real company's business units, products and regions.

Conventions the generator relies on (they wire up the planted situations):
  * processes[1] is the customer-facing process that the critical supplier feeds;
  * suppliers[0] is the critical supplier (entries are [name, category, typical lead time in days]);
  * segments[1] is the segment whose churn rises when processes[1] slows down.
"""

from __future__ import annotations

ARCHETYPES: dict[str, dict] = {
    "retail_consumer": {
        "label": "Retail & consumer",
        "seasonality": [0.90, 0.84, 0.94, 0.96, 0.98, 0.97, 0.99, 0.97, 0.96, 1.02, 1.14, 1.33],
        "price_elasticity": -1.4,
        "default_business_units": [
            {"name": "Stores", "revenue_share": 0.52, "margin_pct": 31, "products": ["Grocery", "Fresh food", "Household"]},
            {"name": "Online", "revenue_share": 0.27, "margin_pct": 26, "products": ["Home delivery", "Click & collect", "Marketplace"]},
            {"name": "Own Brands", "revenue_share": 0.21, "margin_pct": 38, "products": ["Private-label food", "Private-label home"]},
        ],
        "segments": [
            ["Loyalty members", 0.44, 0.6, 46],
            ["Online subscribers", 0.21, 1.2, 38],
            ["Occasional shoppers", 0.27, 3.1, 22],
            ["Business customers", 0.08, 0.9, 41],
        ],
        "processes": [
            ["Store replenishment", "store orders", 36, 0.97],
            ["Online order fulfilment", "orders", 30, 0.97],
            ["Returns & refunds", "returns", 72, 0.95],
            ["Supplier onboarding", "suppliers", 240, 0.90],
        ],
        "suppliers": [
            ["Last-mile delivery partner", "Logistics", 1.5],
            ["Fresh produce co-operative", "Fresh food", 2],
            ["Packaging manufacturer", "Packaging", 21],
            ["Cloud & e-commerce platform", "Technology", 14],
            ["Household goods wholesaler", "Household", 10],
            ["Energy supplier", "Utilities", 30],
        ],
        "site_types": [["Store", 40], ["Distribution centre", 2]],
        "functions": ["Store Operations", "Merchandising", "E-commerce & Tech", "Customer Service", "Supply Chain", "Marketing"],
        "talent_function": "E-commerce & Tech",
        "regulations": [
            ["GDPR", "Customer data and loyalty programme consent"],
            ["Consumer protection", "Pricing transparency and promotions"],
            ["Food safety", "Traceability and cold chain"],
            ["CSRD", "Sustainability reporting incl. Scope 3"],
        ],
        "risks": [
            ["Food inflation squeezes margins", "Finance"],
            ["Peak-season delivery capacity", "Operations"],
            ["Loyalty data breach", "Technology"],
            ["Discounter price war", "Market"],
        ],
        "unit_price_range": [4, 60],
        "arpu_range": [600, 2400],
    },
    "telecom": {
        "label": "Telecommunications",
        "seasonality": [1.00, 0.97, 1.00, 0.99, 1.00, 0.99, 0.98, 0.98, 1.00, 1.01, 1.02, 1.06],
        "price_elasticity": -0.6,
        "default_business_units": [
            {"name": "Consumer Mobile", "revenue_share": 0.45, "margin_pct": 38, "products": ["Postpaid plans", "Prepaid", "Devices"]},
            {"name": "Home Broadband & TV", "revenue_share": 0.30, "margin_pct": 33, "products": ["Fibre broadband", "TV bundles"]},
            {"name": "Business & Wholesale", "revenue_share": 0.25, "margin_pct": 29, "products": ["Enterprise connectivity", "IoT", "Wholesale"]},
        ],
        "segments": [
            ["Postpaid consumers", 0.48, 0.9, 18],
            ["Fibre households", 0.22, 1.1, 12],
            ["SMB customers", 0.17, 1.4, 21],
            ["Enterprise accounts", 0.13, 0.5, 33],
        ],
        "processes": [
            ["Mobile number porting", "port-ins", 24, 0.98],
            ["Fibre installation", "installations", 96, 0.95],
            ["Fault repair", "tickets", 48, 0.93],
            ["Enterprise provisioning", "circuits", 480, 0.90],
        ],
        "suppliers": [
            ["Fibre network equipment vendor", "Network equipment", 35],
            ["Field engineering contractor", "Field services", 7],
            ["Handset distributor", "Devices", 10],
            ["Radio access network vendor", "Network equipment", 60],
            ["Cloud & IT services provider", "Technology", 20],
            ["Energy supplier", "Utilities", 30],
        ],
        "site_types": [["Exchange / core site", 6], ["Retail store", 15]],
        "functions": ["Network Operations", "Sales", "Product & Engineering", "Customer Care", "Field Services", "Marketing"],
        "talent_function": "Product & Engineering",
        "regulations": [
            ["EECC / telecom regulator", "Switching, contract and coverage obligations"],
            ["NIS2", "Network security and incident reporting"],
            ["GDPR & ePrivacy", "Traffic and location data"],
            ["Spectrum licence", "Coverage roll-out commitments"],
        ],
        "risks": [
            ["Price competition from challengers", "Market"],
            ["Fibre roll-out delays", "Operations"],
            ["Major network outage", "Technology"],
            ["Spectrum auction costs", "Finance"],
        ],
        "unit_price_range": [15, 90],
        "arpu_range": [300, 900],
    },
    "financial_services": {
        "label": "Banking & financial services",
        "seasonality": [1.00, 0.98, 1.01, 1.00, 1.00, 0.99, 0.98, 0.97, 1.00, 1.01, 1.01, 1.05],
        "price_elasticity": -0.9,
        "default_business_units": [
            {"name": "Retail Banking", "revenue_share": 0.46, "margin_pct": 34, "products": ["Current accounts", "Mortgages", "Cards"]},
            {"name": "Business Banking", "revenue_share": 0.32, "margin_pct": 39, "products": ["SME lending", "Payments & cash management"]},
            {"name": "Wealth & Insurance", "revenue_share": 0.22, "margin_pct": 42, "products": ["Investment funds", "Life & home insurance"]},
        ],
        "segments": [
            ["Mass-market customers", 0.41, 0.5, 14],
            ["Mortgage holders", 0.26, 0.7, 19],
            ["SME clients", 0.21, 0.9, 24],
            ["Affluent clients", 0.12, 0.4, 37],
        ],
        "processes": [
            ["Account opening", "applications", 48, 0.95],
            ["Mortgage approval", "applications", 240, 0.92],
            ["Card dispute handling", "disputes", 120, 0.94],
            ["SME loan underwriting", "applications", 360, 0.90],
        ],
        "suppliers": [
            ["Property valuation provider", "Valuations", 4],
            ["Core banking platform vendor", "Technology", 30],
            ["Card scheme & processor", "Payments", 14],
            ["KYC & credit data provider", "Data", 2],
            ["Cloud provider", "Technology", 20],
            ["Contact-centre outsourcer", "Operations", 7],
        ],
        "site_types": [["Branch", 25], ["Operations centre", 2]],
        "functions": ["Relationship Management", "Credit & Risk", "Digital & Technology", "Customer Operations", "Compliance", "Marketing"],
        "talent_function": "Digital & Technology",
        "regulations": [
            ["Basel III / CRR", "Capital and liquidity requirements"],
            ["EU DORA", "ICT resilience and incident reporting"],
            ["AML / KYC", "Customer due diligence"],
            ["Consumer Duty / MiFID II", "Fair value and suitability"],
        ],
        "risks": [
            ["Credit losses rise with rates", "Finance"],
            ["Deposit outflows to neobanks", "Market"],
            ["Ransomware on core systems", "Technology"],
            ["AML control failure", "Compliance"],
        ],
        "unit_price_range": [10, 400],
        "arpu_range": [250, 1800],
    },
    "industrial_manufacturing": {
        "label": "Industrial manufacturing",
        "seasonality": [0.94, 0.97, 1.04, 0.99, 1.00, 1.03, 0.93, 0.88, 1.02, 1.03, 1.04, 1.13],
        "price_elasticity": -0.8,
        "default_business_units": [
            {"name": "Automation", "revenue_share": 0.40, "margin_pct": 36, "products": ["Controllers", "Drives", "Industrial software"]},
            {"name": "Smart Infrastructure", "revenue_share": 0.35, "margin_pct": 30, "products": ["Building systems", "Grid equipment"]},
            {"name": "Services", "revenue_share": 0.25, "margin_pct": 41, "products": ["Maintenance contracts", "Spare parts", "Digital services"]},
        ],
        "segments": [
            ["Global OEM accounts", 0.38, 0.3, 34],
            ["Mid-size manufacturers", 0.27, 0.8, 27],
            ["Utilities & public sector", 0.20, 0.2, 31],
            ["Distributors", 0.15, 0.7, 22],
        ],
        "processes": [
            ["Quote to order", "quotes", 72, 0.92],
            ["Order fulfilment", "orders", 336, 0.95],
            ["Field service", "service visits", 96, 0.93],
            ["New product introduction", "projects", 4000, 0.85],
        ],
        "suppliers": [
            ["Semiconductor distributor", "Electronic components", 42],
            ["Precision castings supplier", "Mechanical parts", 28],
            ["Freight forwarder", "Logistics", 12],
            ["Steel & copper trader", "Raw materials", 20],
            ["Contract electronics manufacturer", "Manufacturing services", 35],
            ["Energy supplier", "Utilities", 30],
        ],
        "site_types": [["Plant", 3], ["Warehouse", 1]],
        "functions": ["Manufacturing", "Sales", "R&D & Engineering", "Service", "Supply Chain", "Marketing"],
        "talent_function": "R&D & Engineering",
        "regulations": [
            ["EU Machinery Regulation", "Product safety and CE conformity"],
            ["Export controls", "Dual-use goods screening"],
            ["CSRD & CBAM", "Sustainability reporting and carbon border adjustment"],
            ["NIS2", "Cybersecurity for critical entities"],
        ],
        "risks": [
            ["Component shortages", "Supply chain"],
            ["Energy price spikes at plants", "Finance"],
            ["Engineering talent shortage", "People"],
            ["OT cyber attack", "Technology"],
        ],
        "unit_price_range": [200, 25000],
        "arpu_range": [40000, 900000],
    },
    "energy_utilities": {
        "label": "Energy & utilities",
        "seasonality": [1.22, 1.15, 1.06, 0.95, 0.88, 0.84, 0.86, 0.85, 0.89, 0.98, 1.10, 1.22],
        "price_elasticity": -0.3,
        "default_business_units": [
            {"name": "Retail Energy", "revenue_share": 0.48, "margin_pct": 12, "products": ["Household electricity", "Gas", "Green tariffs"]},
            {"name": "Networks", "revenue_share": 0.30, "margin_pct": 44, "products": ["Grid connections", "Distribution"]},
            {"name": "Renewables", "revenue_share": 0.22, "margin_pct": 52, "products": ["Wind", "Solar", "Battery storage"]},
        ],
        "segments": [
            ["Households", 0.52, 1.6, 9],
            ["SME businesses", 0.19, 1.2, 15],
            ["Green-tariff households", 0.14, 0.8, 26],
            ["Industrial & commercial", 0.15, 0.4, 28],
        ],
        "processes": [
            ["Customer switching", "switches", 72, 0.97],
            ["New grid connection", "connections", 720, 0.90],
            ["Outage restoration", "outages", 6, 0.95],
            ["Smart meter installation", "installations", 168, 0.92],
        ],
        "suppliers": [
            ["Transformer manufacturer", "Grid equipment", 120],
            ["Wind turbine OEM", "Generation equipment", 180],
            ["Smart meter vendor", "Metering", 30],
            ["Civil works contractor", "Field services", 14],
            ["Wholesale energy trader", "Energy", 2],
            ["Billing platform vendor", "Technology", 30],
        ],
        "site_types": [["Substation", 30], ["Wind / solar park", 8]],
        "functions": ["Network Operations", "Sales", "Engineering & Digital", "Customer Service", "Field Operations", "Trading"],
        "talent_function": "Engineering & Digital",
        "regulations": [
            ["Energy regulator price cap", "Retail tariff limits"],
            ["Network licence", "Reliability and connection obligations"],
            ["NIS2", "Critical infrastructure security"],
            ["EU ETS & CSRD", "Emissions and sustainability reporting"],
        ],
        "risks": [
            ["Wholesale price volatility", "Finance"],
            ["Grid connection backlog", "Operations"],
            ["Extreme weather outages", "Operations"],
            ["Bad debt from vulnerable customers", "Finance"],
        ],
        "unit_price_range": [50, 2000],
        "arpu_range": [900, 2600],
    },
    "software_saas": {
        "label": "Software & SaaS",
        "seasonality": [0.95, 0.96, 1.04, 0.97, 0.98, 1.03, 0.96, 0.95, 1.03, 0.99, 1.01, 1.13],
        "price_elasticity": -0.5,
        "default_business_units": [
            {"name": "Core Platform", "revenue_share": 0.55, "margin_pct": 78, "products": ["Enterprise licences", "Team plans"]},
            {"name": "Data & AI", "revenue_share": 0.25, "margin_pct": 71, "products": ["Analytics add-on", "AI assistant"]},
            {"name": "Professional Services", "revenue_share": 0.20, "margin_pct": 24, "products": ["Implementation", "Training"]},
        ],
        "segments": [
            ["Enterprise customers", 0.47, 0.4, 41],
            ["Mid-market customers", 0.28, 1.1, 33],
            ["SMB self-serve", 0.17, 2.6, 28],
            ["Public sector", 0.08, 0.3, 36],
        ],
        "processes": [
            ["Lead to contract", "deals", 720, 0.85],
            ["Customer onboarding", "onboardings", 240, 0.92],
            ["Support ticket resolution", "tickets", 24, 0.95],
            ["Release delivery", "releases", 336, 0.90],
        ],
        "suppliers": [
            ["Cloud infrastructure provider", "Cloud", 3],
            ["Implementation partner", "Professional services", 14],
            ["Payments provider", "Payments", 5],
            ["Data enrichment vendor", "Data", 7],
            ["Customer support outsourcer", "Operations", 5],
            ["Security tooling vendor", "Technology", 20],
        ],
        "site_types": [["Office", 4], ["Cloud region", 2]],
        "functions": ["Sales", "Customer Success", "Engineering", "Support", "Product", "Marketing"],
        "talent_function": "Engineering",
        "regulations": [
            ["GDPR", "Customer data processing and transfers"],
            ["EU AI Act", "Obligations for AI features"],
            ["SOC 2 / ISO 27001", "Security controls customers rely on"],
            ["NIS2", "Incident reporting for digital providers"],
        ],
        "risks": [
            ["Net revenue retention falls", "Market"],
            ["Cloud cost overruns", "Finance"],
            ["Security breach", "Technology"],
            ["Key engineer attrition", "People"],
        ],
        "unit_price_range": [20, 6000],
        "arpu_range": [3000, 120000],
    },
}

ARCHETYPE_NAMES = sorted(ARCHETYPES)

# Extra industry detail used by the four agent types (resilience, margin & cash, customer rescue, growth):
#   account_segments   indexes of the segments that hold the key accounts (B2B or partner contracts)
#   account_suffixes   customer types used in key-account labels ("Platinum account · Pharmacies · Germany")
#   contact_roles      who the account team talks to (roles only — no personal data)
#   systems            [name, type, capacity headroom %, single point of failure?, process indexes it supports]
#   regulatory_buffer  [name, unit, current, threshold, monthly change, higher is better?]
#   opportunities      adjacent growth plays the industry is pursuing
#   competitors        competitor archetypes in the market landscape
#   friction_themes    [complaint theme, process index]
EXTRAS: dict[str, dict] = {
    "retail_consumer": {
        "account_segments": [3],
        "account_suffixes": ["Hotels", "Catering", "Office Supplies", "Pharmacies", "Schools", "Fitness Clubs", "Cafés", "Care Homes"],
        "contact_roles": ["Head of Procurement", "Operations Director", "Category Buyer"],
        "systems": [["Order management system", "platform", 9, True, [1, 2]],
                    ["Warehouse management system", "platform", 31, False, [0, 1]],
                    ["E-commerce storefront", "digital channel", 44, False, [1]],
                    ["Store point-of-sale network", "infrastructure", 38, False, [0]]],
        "regulatory_buffer": ["Cold-chain compliance (audited sites passing)", "%", 98.4, 95.0, -0.6, True],
        "opportunities": ["Quick commerce (30-minute delivery)", "Retail media network", "Subscription grocery boxes", "B2B office & catering supply"],
        "competitors": ["Hard discounter", "Online pure-player", "Quick-commerce start-up"],
        "friction_themes": [["Late home deliveries", 1], ["Missing or substituted items", 1], ["Refund delays", 2], ["Out-of-stock in store", 0]],
    },
    "telecom": {
        "account_segments": [2, 3],
        "account_suffixes": ["Logistics", "Healthcare", "Bank", "Retail Group", "Hotels", "Manufacturing", "Insurance", "Media"],
        "contact_roles": ["Head of IT Infrastructure", "CIO", "Procurement Manager"],
        "systems": [["Service activation platform", "platform", 8, True, [0, 1, 3]],
                    ["Fibre network inventory", "platform", 27, False, [1]],
                    ["Mobile core network", "infrastructure", 35, False, [0, 2]],
                    ["Field workforce scheduler", "platform", 22, False, [1, 2]]],
        "regulatory_buffer": ["Network availability vs licence obligation", "%", 99.95, 99.9, -0.01, True],
        "opportunities": ["Private 5G for industrial sites", "Managed SD-WAN for SMEs", "IoT fleet connectivity", "Home energy & broadband bundles"],
        "competitors": ["National incumbent", "Low-cost challenger", "Cable operator"],
        "friction_themes": [["Missed installation appointments", 1], ["Slow fault repair", 2], ["Porting delays", 0], ["Billing errors", 2]],
    },
    "financial_services": {
        "account_segments": [2],
        "account_suffixes": ["Builders", "Logistics", "Foods", "Engineering", "Pharma", "Retail", "Energy", "Software"],
        "contact_roles": ["Finance Director", "Treasurer", "CFO"],
        "systems": [["Loan origination system", "platform", 7, True, [1, 3]],
                    ["Core banking platform", "platform", 33, False, [0, 1, 2, 3]],
                    ["Mobile banking app", "digital channel", 41, False, [0, 2]],
                    ["Payments hub", "infrastructure", 29, False, [2]]],
        "regulatory_buffer": ["Liquidity coverage ratio", "%", 131.0, 110.0, -2.5, True],
        "opportunities": ["Embedded finance for SME platforms", "Green mortgages & retrofit loans", "Digital wealth for the mass-affluent", "Banking-as-a-service"],
        "competitors": ["Neobank", "Large universal bank", "Fintech lender"],
        "friction_themes": [["Slow mortgage decisions", 1], ["Account opening paperwork", 0], ["Card dispute delays", 2], ["App outages", 0]],
    },
    "industrial_manufacturing": {
        "account_segments": [0, 1, 2, 3],
        "account_suffixes": ["Automotive", "Packaging", "Utilities", "Chemicals", "Food Processing", "Rail", "Pharma", "Building Services"],
        "contact_roles": ["Plant Director", "Head of Procurement", "Maintenance Manager"],
        "systems": [["ERP & MRP system", "platform", 10, True, [0, 1]],
                    ["Manufacturing execution system", "platform", 26, False, [1]],
                    ["Field service management", "platform", 34, False, [2]],
                    ["Product lifecycle management", "platform", 40, False, [3]]],
        "regulatory_buffer": ["Safety stock of critical components", "days", 18.0, 10.0, -1.6, True],
        "opportunities": ["Equipment-as-a-service", "Predictive maintenance subscriptions", "Energy-efficiency retrofits", "Aftermarket parts e-commerce"],
        "competitors": ["Global conglomerate", "Asian low-cost manufacturer", "Specialist niche player"],
        "friction_themes": [["Late order deliveries", 1], ["Spare parts availability", 2], ["Quote turnaround", 0], ["Commissioning delays", 1]],
    },
    "energy_utilities": {
        "account_segments": [1, 3],
        "account_suffixes": ["Data Centres", "Steel", "Hospitals", "Retail Parks", "Cold Storage", "Universities", "Water Utility", "Chemicals"],
        "contact_roles": ["Energy Manager", "Facilities Director", "Head of Procurement"],
        "systems": [["Grid connection management system", "platform", 6, True, [1]],
                    ["Billing & CRM platform", "platform", 28, False, [0, 3]],
                    ["SCADA / grid control", "infrastructure", 37, False, [2]],
                    ["Smart meter head-end", "platform", 24, False, [3]]],
        "regulatory_buffer": ["Generation reserve margin", "%", 12.5, 8.0, -0.7, True],
        "opportunities": ["Home battery & solar bundles", "EV charging for fleets", "Heat-pump installation", "Grid flexibility services"],
        "competitors": ["Former state incumbent", "Green challenger", "Oil major's retail arm"],
        "friction_themes": [["Grid connection waiting times", 1], ["Estimated bills", 0], ["Smart meter appointments", 3], ["Outage communication", 2]],
    },
    "software_saas": {
        "account_segments": [0, 1, 3],
        "account_suffixes": ["Health", "Insurance", "Logistics", "Retail", "Bank", "Media", "Telecom", "Government"],
        "contact_roles": ["CIO", "VP Engineering", "Head of Procurement"],
        "systems": [["Provisioning & tenant service", "platform", 8, True, [1]],
                    ["Core application cluster", "infrastructure", 30, False, [1, 2, 3]],
                    ["Data pipeline", "platform", 25, False, [1]],
                    ["Billing & subscription system", "platform", 36, False, [0]]],
        "regulatory_buffer": ["Uptime vs contractual SLA", "%", 99.96, 99.9, -0.01, True],
        "opportunities": ["Usage-based AI tier", "Industry edition for healthcare", "Partner marketplace", "Premium SLA & support tier"],
        "competitors": ["Hyperscaler bundle", "Open-source alternative", "Category leader"],
        "friction_themes": [["Slow onboarding", 1], ["Support response times", 2], ["Missing integrations", 1], ["Release regressions", 3]],
    },
}

# Approximate exchange rates: units of each currency per 1 EUR.
FX_PER_EUR = {"EUR": 1.0, "USD": 1.09, "GBP": 0.86, "SEK": 11.4, "NOK": 11.6, "DKK": 7.46, "CHF": 0.95, "PLN": 4.3,
              "JPY": 162.0, "INR": 91.0, "CNY": 7.8, "AUD": 1.64, "CAD": 1.48, "BRL": 5.9, "SGD": 1.46}

REGION_CURRENCY = [
    (("united kingdom", "uk", "britain", "england"), "GBP"),
    (("united states", "usa", "us", "north america", "americas"), "USD"),
    (("sweden", "nordics", "scandinavia"), "SEK"), (("norway",), "NOK"), (("denmark",), "DKK"),
    (("switzerland",), "CHF"), (("poland",), "PLN"), (("japan",), "JPY"), (("india",), "INR"), (("china",), "CNY"),
    (("australia",), "AUD"), (("canada",), "CAD"), (("brazil", "latin america", "latam"), "BRL"),
    (("singapore", "asia", "apac", "asia-pacific"), "SGD"),
]
