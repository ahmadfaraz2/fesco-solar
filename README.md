# ☀️ fesco-solar

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Package Manager: uv](https://img.shields.io/badge/package%20manager-uv-8A2BE2.svg)](https://github.com/astral-sh/uv)
[![CLI: Typer & Rich](https://img.shields.io/badge/CLI-Typer%20%26%20Rich-orange.svg)](https://typer.tiangolo.com/)
[![Tests: Pytest 18/18 Passed](https://img.shields.io/badge/tests-18%2F18%20passing-brightgreen.svg)](https://pytest.org)
[![Regulatory: NEPRA S.R.O. 892(I)](https://img.shields.io/badge/regulations-NEPRA%20Net--Metering-green.svg)](https://nepra.org.pk/)

> **Intelligent Rooftop Photovoltaic (PV) Sizing, Bill Extractor & Turnkey BOS Payback Advisor for FESCO Consumers in Punjab.**

`fesco-solar` is an end-to-end Python CLI application engineered for residential, commercial, and agricultural electricity consumers in the **Faisalabad Electric Supply Company (FESCO)** territory (Faisalabad, Sargodha, Jhang, Toba Tek Singh, Chiniot, and Bhakkar).

Managed with [**uv**](https://github.com/astral-sh/uv), `fesco-solar` features a modular architecture, Pydantic v2 data models, direct live scraping of official **PITC** billing portals, seasonal swing analysis, Punjab irradiance calibration (~125 units/kWp/month), NEPRA sanctioned load checks, dynamic per-watt solar plate pricing in PKR, and comprehensive Turnkey Balance of System (BOS) financial modeling.

---

## 🚀 Key Highlights & Capabilities

### 1. Dual Bill Extraction (Live Portal & Local PDF)
- **Live Online PITC Billing Portal:** Queries `https://bill.pitc.com.pk/fescobill` with full ASP.NET viewstate and RU code (`U` for Urban, `R` for Rural) negotiation to extract genuine, live consumer records and 12 months of consumption history.
- **Local PDF Bills:** Uses `pdfplumber` with stream-level regex parsing to process computerized FESCO electricity bills offline.

### 2. Punjab-Calibrated Solar Sizing Engine
- **Seasonal Swing Analysis:** Analyzes the ratio between extreme summer air-conditioning peak demand (May–August) and winter lows (December–February) to avoid summer tariff slab penalties.
- **Punjab Solar Irradiance Profile:** Calibrated to the regional solar irradiance curve of Central/Southern Punjab (**~125 kWh/kWp/month average**), incorporating winter smog/fog derating in December/January (0.72–0.76x) and peak irradiance in April–June (1.16–1.24x).
- **NEPRA Regulatory Compliance:** Validates inverter capacity against the consumer's **Sanctioned Load** under NEPRA Distributed Generation Regulations (S.R.O. 892(I)/2015 & updates). Flags necessary load extensions and 3-phase prerequisites before application.

### 3. Dynamic Pricing & Turnkey BOS Cost Engine
- **Live Market Rates (PKR/Watt):** Scrapes live per-watt market prices for Tier-1 solar modules (Longi, Jinko, JA Solar, Canadian Solar) with persistent TTL caching in `data/rates_cache.json`.
- **Complete Turnkey Balance of System (BOS):** Models total installed costs:
  - Tier-1 N-Type TOPCon / HPBC PV modules.
  - Three-phase on-grid string or hybrid inverters (1.15–1.25x DC/AC ratio).
  - Heavy-duty custom Galvanized Iron (GI) L2/L3 mounting structures (140 km/h wind rating).
  - Electrical BOS: DC flexible copper cables (4/6 mm²), AC cables, Schneider/ABB breakers, Type-II Surge Protection Devices (SPD), IP65 distribution boxes.
  - Chemical earthing & grounding bore (< 5 ohms resistance) with copper rods.
  - FESCO Net Metering facilitation: Bi-directional 3-phase green meter, WAPDA testing lab NOC, and NEPRA license facilitation.
  - Turnkey civil foundations, trunking, installation labor, and commissioning.

### 4. Financial Feasibility & 25-Year Payback
- Calculates direct daytime self-consumption vs. green meter export units.
- Evaluates avoided grid purchases under FESCO domestic slab tariffs (~Rs 52–58/unit) and export buyback credits under NEPRA rules (~Rs 22/unit).
- Calculates Simple Payback Period (years), annual Return on Investment (ROI %), 25-year cumulative net savings, and Levelized Cost of Energy (LCOE in PKR/unit).

---

## 📦 Installation & Setup (Managed with uv)

```bash
# Clone the repository
git clone https://github.com/ahmadfaraz2/fesco-solar.git
cd fesco-solar

# Create virtual environment with uv (Python 3.10+)
uv venv --python 3.10

# Sync dependencies and lockfile
uv sync
```

---

## ⚡ CLI Usage & Commands

```
Usage: fesco-solar [OPTIONS] COMMAND [ARGS]...

Commands:
  analyze      Analyze a FESCO electricity bill (online reference or PDF).
  rates        Display live per-watt solar plate rates in PKR.
  quick-quote  Generate instant solar sizing and turnkey quote based on units.
  demo         Run an end-to-end demonstration with a realistic bill.
```

### 1. Analyze an Online Bill via 14-Digit Reference Number
Fetch live data directly from the PITC portal using any 14-digit FESCO reference number:
```bash
uv run fesco-solar analyze --ref 14134352211500
```
*(Optionally include the RU code at the end if known, e.g. `14134352211500R`).*

### 2. Analyze a Local PDF Bill
```bash
uv run fesco-solar analyze --pdf data/sample_fesco_bill.pdf
```

### 3. Sizing for Hybrid Inverter with Battery Backup
```bash
uv run fesco-solar analyze --ref 14134352211500 --type hybrid
```

### 4. Custom Capacity Override (Manual kW)
```bash
uv run fesco-solar analyze --ref 14134352211500 --kw 10.0
```

### 5. Check Live Solar Plate Rates in Pakistan (PKR/Watt)
```bash
# View cached rates
uv run fesco-solar rates

# Force fresh live scrape of Pakistani solar market
uv run fesco-solar rates --refresh
```

### 6. Quick Solar Quote (No Bill Needed)
Provide average monthly consumption (units) and sanctioned load for an instant quote:
```bash
uv run fesco-solar quick-quote --units 850 --load 6.0
```

### 7. Sanctioned Load Check in Action
```bash
# When consumption requires 12 kW but connection is sanctioned for only 5 kW:
uv run fesco-solar quick-quote --units 1600 --load 5.0
```
*Outputs an alert specifying that a +7.0 kW load extension application with FESCO is required under NEPRA regulations before net metering inspection.*

### 8. End-to-End Walkthrough Demo
```bash
uv run fesco-solar demo
```

---

## 🔍 Verified Real-World Case Study (`14134352211500 R`)

When querying reference number **`14134352211500`**, `fesco-solar` negotiates with the official PITC server and pulls the following live bill:

```
╭───────── 👤 Consumer & Connection Profile (Original Bill Verified) ──────────╮
│                                                                              │
│    Consumer Name:     Liaquat Ali,       Reference          14134352211500R  │
│                       S/O Muhammad       Number:                             │
│                       Sharif                                                 │
│    Address:           Chak No.24 Nb      Sanctioned         3.0 kW           │
│                       Bhalwal            Load:              (1-Phase)        │
│    Tariff             A-1A(01)           Feeder /           024317           │
│    Category:          Domestic           Sub-Div:           Destgheer /      │
│                                                             Purana Bhalwal   │
│    Status:            🟢 ORIGINAL        Billing Month:     SEP 26           │
│                       PITC LIVE BILL                                         │
│                       VERIFIED                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
        📊 12-Month Billing History & Seasonal Swings (Total: 3,048 kWh)        
╭──────────────┬─────────────┬────────────┬───────────────────────────┬────────╮
│ Month        │ Units (kWh) │ Bill (PKR) │ Seasonal Swing Indicator  │ Status │
├──────────────┼─────────────┼────────────┼───────────────────────────┼────────┤
│ SEP25        │         286 │  Rs 10,899 │ █████████████             │  PAID  │
│ OCT25        │         262 │  Rs 10,842 │ ████████████              │  PAID  │
│ NOV25        │         193 │  Rs 18,836 │ █████████                 │  PAID  │
│ DEC25        │         157 │   Rs 5,806 │ ███████ WINTER LOW        │  PAID  │
│ JAN26        │         203 │   Rs 8,695 │ █████████                 │  PAID  │
│ FEB26        │         182 │  Rs 16,842 │ ████████                  │  PAID  │
│ MAR26        │         191 │   Rs 8,887 │ █████████                 │  PAID  │
│ APR26        │         246 │  Rs 12,352 │ ███████████               │  PAID  │
│ MAY26        │         261 │  Rs 12,697 │ ████████████              │  PAID  │
│ JUN26        │         314 │  Rs 16,278 │ ███████████████           │  PAID  │
│ JUL26        │         414 │  Rs 21,791 │ ████████████████████ PEAK │  PAID  │
│ AUG26        │         339 │  Rs 16,997 │ ████████████████          │  PAID  │
├──────────────┼─────────────┼────────────┼───────────────────────────┼────────┤
│ Annual / Avg │   3,048 kWh │ Rs 160,922 │                           │        │
╰──────────────┴─────────────┴────────────┴───────────────────────────┴────────╯
```

### Engineered Solution for this Consumer:
- **Recommended System:** 3.51 kWp DC (6 × 585W Longi Hi-MO 6 Explorer N-Type Panels).
- **Inverter Capacity:** 3.0 kW Three-Phase String Inverter.
- **Rooftop Area Required:** ~246 sq. ft (~1.1 Marla).
- **Compliance Status:** Inverter capacity (3.0 kW) is within sanctioned load (3.0 kW). Single-phase meter (`S-P 510663`) flagged for 3-phase conversion before green meter commissioning.
- **Turnkey CapEx Investment:** **Rs 589,150** (167.85 PKR/Watt complete turnkey).
- **Annual Savings:** **Rs 190,135 / year** (Rs 15,845 / month).
- **Payback Horizon:** **3.1 Years** (Annual ROI: **32.3%**).
- **25-Year Net Financial Savings:** **Rs 4,164,225**.
- **Levelized Cost of Energy (LCOE):** **Rs 5.54 / unit** (vs grid tariff of Rs ~54.00/unit).

---

## 📂 Project Architecture

```
fesco-solar/
├── pyproject.toml              # Modern packaging & CLI entrypoints (uv managed)
├── README.md                   # Comprehensive documentation
├── uv.lock                     # Deterministic dependency lockfile
├── data/
│   ├── rates_cache.json        # Dynamic rates cache (live scraped in PKR)
│   ├── sample_fesco_bill.pdf   # Computerized sample FESCO bill
│   └── generate_sample_pdf.py  # Sample PDF generator utility
├── src/
│   └── fesco_solar/
│       ├── __init__.py         # Package entrypoint & version
│       ├── models/             # Pydantic v2 data models
│       │   ├── compat.py       # Zero-dependency compat layer (instant execution)
│       │   ├── bill.py         # ConsumerDetails, ElectricityBill, MonthlyRecord
│       │   ├── solar.py        # SolarPanelSpec, PunjabSolarProfile, SystemRecommendation
│       │   ├── pricing.py      # SolarPlateRate, RatesCache, TurnkeyBOSCost
│       │   └── financial.py    # FinancialSummary
│       ├── extractors/         # Bill extractors
│       │   ├── base.py         # Abstract BaseBillExtractor & regex parsers
│       │   ├── pitc_online.py  # PITC online portal scraper (14-digit ref + RU code)
│       │   └── pdf_parser.py   # pdfplumber PDF bill parser
│       ├── engine/             # Physics & sizing engine
│       │   └── sizing.py       # Punjab irradiance & sanctioned load validator
│       ├── pricing/            # Dynamic pricing & Turnkey BOS
│       │   ├── service.py      # Live scraper, cache & Turnkey BOS calculator
│       │   └── payback.py      # Net metering tariffs & financial ROI engine
│       └── cli/                # Rich terminal UI
│           └── main.py         # Typer commands & tables
└── tests/                      # Automated test suite (18/18 passing)
    ├── test_models.py
    ├── test_sizing.py
    ├── test_extractors.py
    ├── test_pricing.py
    └── test_cli.py
```

---

## 🧪 Automated Testing

Run the full pytest suite:

```bash
uv run pytest -v
```

All 18 tests execute across models, extractors, sizing calculations, pricing cache, and CLI subcommands:
```
tests/test_cli.py::test_cli_help PASSED                                  [  5%]
tests/test_cli.py::test_cli_rates PASSED                                 [ 11%]
tests/test_cli.py::test_cli_quick_quote PASSED                           [ 16%]
tests/test_cli.py::test_cli_analyze_online_ref PASSED                    [ 22%]
tests/test_cli.py::test_cli_demo PASSED                                  [ 27%]
tests/test_extractors.py::test_pitc_extractor_valid_14_digit PASSED      [ 33%]
tests/test_extractors.py::test_pitc_extractor_invalid_short_ref PASSED   [ 38%]
tests/test_extractors.py::test_pdf_extractor_nonexistent_file PASSED     [ 44%]
tests/test_models.py::test_consumer_details_clean_reference PASSED       [ 50%]
tests/test_models.py::test_electricity_bill_computed_fields PASSED       [ 55%]
tests/test_models.py::test_punjab_solar_profile PASSED                   [ 61%]
tests/test_models.py::test_turnkey_bos_cost_breakdown PASSED             [ 66%]
tests/test_pricing.py::test_pricing_service_cache PASSED                 [ 72%]
tests/test_pricing.py::test_turnkey_bos_calculation PASSED               [ 77%]
tests/test_pricing.py::test_financial_payback_engine PASSED              [ 83%]
tests/test_sizing.py::test_sizing_within_sanctioned_load PASSED          [ 88%]
tests/test_sizing.py::test_sizing_exceeding_sanctioned_load PASSED       [ 94%]
tests/test_sizing.py::test_custom_kw_override PASSED                     [100%]

============================= 18 passed in ~8s ==============================
```

---

## ⚖️ Regulatory References & Engineering Benchmarks

- **Punjab Specific Solar Generation Benchmark:** ~125 kWh / kWp / Month (annual average yield of 1,500 kWh/kWp).
- **NEPRA Alternative & Renewable Energy Regulations (S.R.O. 892(I)/2015 & updates):** Installed Distributed Generation capacity cannot exceed 100% of consumer sanctioned load.
- **Three-Phase Requirement:** Net metering requires a 3-Phase connection for bi-directional green meter installation.
- **NEPRA Buyback Rate:** Distributed Generation export credits calculated at ~PKR 22/unit.

---

## 📄 License

MIT License. Developed for solar energy optimization and distributed generation adoption in Pakistan.
