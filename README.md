# ☀️ fesco-solar

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Package Manager: uv](https://img.shields.io/badge/package%20manager-uv-8A2BE2.svg)](https://github.com/astral-sh/uv)
[![CLI: Typer & Rich](https://img.shields.io/badge/CLI-Typer%20%26%20Rich-orange.svg)](https://typer.tiangolo.com/)
[![Regulatory: NEPRA Net-Metering](https://img.shields.io/badge/regulations-NEPRA%20Net--Metering-green.svg)](https://nepra.org.pk/)

> **Rooftop Solar PV Sizing, Bill Extractor & Turnkey BOS Payback Advisor for FESCO Consumers in Punjab.**

`fesco-solar` is a Python CLI application engineered for residential, commercial, and agricultural consumers in the **Faisalabad Electric Supply Company (FESCO)** territory. It extracts electricity bills directly from the official PITC online portal or local PDFs, sizes solar systems calibrated to Punjab irradiance, validates compliance with NEPRA sanctioned load limits, pulls live per-watt plate rates in PKR, and computes complete Turnkey Balance of System (BOS) financial payback.

---

## 🚀 What It Does

* **Dual Bill Extraction:**
  * **Online Portal:** Pulls live consumer records and 12-month billing history from `bill.pitc.com.pk/fescobill` via 14-digit reference number.
  * **Local PDF:** Extracts data from computerized FESCO electricity bills offline via `pdfplumber`.
* **Punjab-Calibrated Solar Sizing:** Calibrated for Punjab solar yield (~125 kWh/kWp/month average), factoring in summer AC peak demand and winter smog derating.
* **NEPRA Regulatory Compliance:** Verifies proposed inverter capacity against the consumer's **Sanctioned Load** under NEPRA Distributed Generation Regulations (flags required load extensions or single-to-3-phase upgrades).
* **Live Market Pricing (PKR/Watt):** Scrapes live per-watt prices for Tier-1 solar panels (Longi, Jinko, Canadian Solar, JA Solar, Trina, Inverex) from `https://solarpanelsprice.pk` with local 24-hour caching (`data/rates_cache.json`).
* **Turnkey Balance of System (BOS) Costing:** Estimates complete installation costs: panels, on-grid/hybrid inverters, GI L2/L3 frames, electrical BOS (cables, breakers, SPDs), chemical earthing bore, and green meter facilitation.
* **Financial Payback Analysis:** Computes simple payback period (years), annual ROI %, 25-year cumulative net savings, and Levelized Cost of Energy (LCOE in PKR/unit) under NEPRA net-metering buyback rules.

---

## 📦 How to Setup

Managed with [**uv**](https://github.com/astral-sh/uv) (supports Linux, macOS, Windows, and Android Termux):

```bash
# 1. Clone repository
git clone https://github.com/ahmadfaraz2/fesco-solar.git
cd fesco-solar

# 2. Create virtual environment (Python 3.10+)
uv venv --python 3.10

# 3. Install dependencies
uv sync
```

---

## ⚡ How to Run

### 1. Analyze an Online Bill (via 14-digit Reference Number)
Fetch live data directly from the PITC portal:
```bash
uv run fesco-solar analyze --ref 14123456789012
```
*(Optionally append the RU code if known, e.g. `14123456789012R`).*

### 2. Analyze a Local PDF Bill
```bash
uv run fesco-solar analyze --pdf data/sample_fesco_bill.pdf
```

### 3. Sizing for Hybrid Inverter (with Battery Backup)
```bash
uv run fesco-solar analyze --ref 14123456789012 --type hybrid
```

### 4. Custom Capacity Override (Manual kW)
```bash
uv run fesco-solar analyze --ref 14123456789012 --kw 10.0
```

### 5. Check Live Solar Plate Rates in Pakistan
```bash
# View cached rates
uv run fesco-solar rates

# Force fresh live scrape from solar market
uv run fesco-solar rates --refresh
```

### 6. Quick Solar Quote (No Bill Needed)
Provide average monthly units and sanctioned load for an instant quote:
```bash
uv run fesco-solar quick-quote --units 850 --load 6.0
```

### 7. Run End-to-End Walkthrough Demo
```bash
uv run fesco-solar demo
```

---

## 📂 Project Structure

```
fesco-solar/
├── pyproject.toml              # Project metadata & CLI scripts
├── data/                       # Local rates cache & sample bills
├── src/fesco_solar/
│   ├── models/                 # Pydantic v2 data models
│   ├── extractors/             # PITC online scraper & PDF parser
│   ├── engine/                 # Solar sizing & NEPRA compliance
│   ├── pricing/                # Live scraping, caching & BOS payback
│   └── cli/                    # Typer & Rich interactive CLI
└── tests/                      # Automated test suite (18 tests)
```

---

## 📄 License

MIT License.
