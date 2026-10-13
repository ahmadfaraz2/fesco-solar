# ☀️ fesco-solar

> **Intelligent Rooftop Solar Sizing, Bill Extractor & Payback Advisor for FESCO Consumers in Punjab.**

`fesco-solar` is a modern, modular Python CLI application built to empower residential, commercial, and agricultural electricity consumers in the Faisalabad Electric Supply Company (FESCO) service area to design and evaluate rooftop photovoltaic (PV) solar installations with precision.

Managed with [uv](https://github.com/astral-sh/uv), `fesco-solar` leverages Pydantic v2 data models, Punjab-specific solar irradiance benchmarks (~125 units/kWp/month), NEPRA Net Metering regulations, live per-watt solar plate scrapers, and Turnkey Balance of System (BOS) cost modeling.

---

## 🚀 Key Features

1. **Dual Bill Extraction:**
   - **Online PITC Portal:** Fetches and parses 12-month billing history and consumer data via 14-digit FESCO reference numbers directly from the PITC portal.
   - **Local PDF Bills:** Parses local computerized FESCO bills via `pdfplumber` with fallback heuristics.
2. **Punjab-Calibrated Solar Sizing Engine:**
   - Accounts for extreme seasonal swings in Punjab (e.g., intense cooling/AC demand in May–August vs winter lows).
   - Calibrated for Punjab's solar irradiance curve (averaging ~125 kWh/kWp/month, factoring winter fog/smog in Dec/Jan).
   - Strict NEPRA compliance validation: cross-references system capacity against consumer's sanctioned load (flags required load extensions).
3. **Dynamic Pricing & Turnkey BOS Cost Engine:**
   - Scrapes live per-watt solar plate prices in PKR from Pakistani solar market indices for Tier-1 brands (Longi, Jinko, JA Solar, Canadian Solar).
   - Persistent TTL caching in `data/rates_cache.json`.
   - Comprehensive Turnkey BOS costing: Tier-1 modules, string/hybrid inverters, custom GI L2/L3 structures, electrical BOS (cables, Schneider breakers, SPDs), chemical earthing bore, FESCO green meter facilitation, and civil/labor commissioning.
4. **Financial Feasibility & Payback Analysis:**
   - Analyzes self-consumption vs export under NEPRA Net Metering buyback tariffs.
   - Computes simple payback period (years), first-year ROI (%), 25-year lifecycle savings, and Levelized Cost of Energy (LCOE in PKR/kWh).
5. **Polished CLI Interface:**
   - Styled with `typer` and `rich` including stylized tables, ASCII seasonal consumption bar charts, colored alert callouts, and financial dashboards.

---

## 📦 Installation & Setup (with uv)

```bash
# Clone or navigate to the project directory
cd fesco-solar

# Create virtual environment with uv (Python 3.10+)
uv venv --python 3.10

# Sync dependencies using uv
uv sync
```

---

## ⚡ CLI Usage & Commands

### 1. Analyze an Online Bill via 14-Digit Reference Number
Query the PITC billing portal, extract consumer data, and run solar sizing:
```bash
uv run fesco-solar analyze --ref "13 13124 1234567 U"
```

### 2. Analyze a Local PDF Bill
Extract consumption history directly from a downloaded FESCO PDF bill:
```bash
uv run fesco-solar analyze --pdf data/sample_fesco_bill.pdf
```

### 3. Sizing for Hybrid Inverter with Battery Backup
```bash
uv run fesco-solar analyze --ref "13131241234567U" --type hybrid
```

### 4. Custom Capacity Override
```bash
uv run fesco-solar analyze --ref "13131241234567U" --kw 10.0
```

### 5. Check Live Solar Plate Rates in PKR
View live per-watt plate rates and force a live scraper update:
```bash
# View cached rates
uv run fesco-solar rates

# Force fresh scrape of Pakistan solar marketplace
uv run fesco-solar rates --refresh
```

### 6. Quick Solar Quote (No Bill Needed)
Provide average monthly consumption (units) and sanctioned load for an instant quote:
```bash
uv run fesco-solar quick-quote --units 850 --load 7.0
```

### 7. Run Full Walkthrough Demo
```bash
uv run fesco-solar demo
```

---

## 📂 Project Structure

```
fesco-solar/
├── pyproject.toml              # Project dependencies & CLI entrypoints (uv managed)
├── README.md                   # Comprehensive documentation
├── data/
│   ├── rates_cache.json        # Cached live solar rates in PKR
│   └── sample_fesco_bill.pdf   # Computerized sample FESCO bill
├── src/
│   └── fesco_solar/
│       ├── __init__.py
│       ├── models/             # Pydantic v2 data models
│       │   ├── bill.py         # ConsumerDetails, ElectricityBill, MonthlyRecord
│       │   ├── solar.py        # SolarPanelSpec, PunjabSolarProfile, SystemRecommendation
│       │   ├── pricing.py      # SolarPlateRate, RatesCache, TurnkeyBOSCost
│       │   └── financial.py    # FinancialSummary
│       ├── extractors/         # Bill extractors
│       │   ├── base.py         # Abstract BaseBillExtractor & regex parsers
│       │   ├── pitc_online.py  # PITC online portal scraper (14-digit ref)
│       │   └── pdf_parser.py   # pdfplumber PDF bill parser
│       ├── engine/             # Sizing & physics calculations
│       │   └── sizing.py       # Punjab irradiance & sanctioned load validator
│       ├── pricing/            # Dynamic pricing & Turnkey BOS
│       │   ├── service.py      # Live scraper, cache & Turnkey BOS calculator
│       │   └── payback.py      # Net metering tariffs & financial ROI engine
│       └── cli/                # Rich terminal UI
│           └── main.py         # Typer commands & tables
└── tests/                      # Pytest automated test suite
    ├── test_models.py
    ├── test_sizing.py
    ├── test_extractors.py
    ├── test_pricing.py
    └── test_cli.py
```

---

## 🧪 Testing

Run the test suite with pytest:
```bash
uv run pytest -v
```

---

## ⚖️ Regulatory Reference (NEPRA & FESCO)
- **Punjab Solar Generation Benchmark:** ~125 kWh / kWp / Month.
- **NEPRA Net Metering Regulations (S.R.O. 892(I)/2015):** Installed Distributed Generation capacity cannot exceed 100% of consumer sanctioned load.
- **Three-Phase Prerequisite:** Net metering requires a 3-Phase connection for bi-directional green meter installation.
