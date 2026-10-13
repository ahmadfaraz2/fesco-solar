# PDF Extractor Overhaul & Fix Specification

> **Task Prompt for Antigravity / AI Agent:**
> Overhaul the PDF bill extractor in `src/fesco_solar/extractors/pdf_parser.py` to eliminate all hardcoded/dummy fallback data and implement genuine, robust extraction for official FESCO / PITC electricity bills.

---

## 🚨 Problem Statement

The current implementation in `src/fesco_solar/extractors/pdf_parser.py` falls back to **synthetic/dummy data** whenever a PDF fails to parse cleanly:
- Fallback reference number: `"13131241234567U"`
- Fallback consumer name: `"FESCO Consumer"`
- Fallback address: `"Faisalabad, Punjab"`
- Fallback load: `6.0 kW`
- Fallback tariff: `"A-1a(01)"`
- **Fallback synthetic history:** Generates 12 fake months using hardcoded multipliers (`base_u * w` with weights `[0.8, 0.55, 0.45, ...]`).

### Why this is unacceptable:
1. When a user provides a real FESCO PDF bill, they expect **their actual electricity data** to be analyzed.
2. Silent dummy fallbacks give the user false sizing recommendations based on made-up consumption figures.
3. If a PDF cannot be parsed, the system **must fail loudly and transparently** with clear diagnostics explaining what could not be extracted and why.

---

## 🎯 Requirements & Acceptance Criteria

### 1. Zero Dummy Data Policy
- **No synthetic history generation.** Never generate fake months or hardcoded multipliers.
- **No hardcoded consumer info.** If reference number, load, or tariff cannot be found, raise a clear `PdfExtractionError`.
- **Strict Minimum Thresholds:** A valid bill must have:
  - Valid 14-digit reference number (with optional RU code).
  - Valid Sanctioned Load (numeric kW).
  - At least 1 month of consumption data (ideally 6–12 months of historical records).
  - If fewer than 3 months of history are detected, do NOT invent data—either ask for explicit confirmation or raise a descriptive validation error with the raw text snippet.

### 2. Anatomy of Genuine FESCO / PITC Bills
Official FESCO computerized bills (both downloaded digital PDFs and print exports) follow a standardized PITC template:

```
+-------------------------------------------------------------------------------+
| FAISALABAD ELECTRIC SUPPLY COMPANY (FESCO)                                    |
| ELECTRICITY CONSUMER BILL                                                     |
+-------------------------------------------------------------------------------+
| REFERENCE NO: 14 13435 2211500 R     | TARIFF: A-1a(01) DOMESTIC              |
| CONSUMER ID: 02431711500             | SANCTIONED LOAD: 3.00 KW               |
| NAME: LIAQUAT ALI S/O M. SHARIF      | CONNECTION DATE: 12-OCT-2014           |
| ADDRESS: PURANA BHALWAL SARGODHA     | METER NO: 510663 (SINGLE PHASE)        |
+-------------------------------------------------------------------------------+
| BILLING HISTORY (LAST 12 MONTHS):                                             |
| MONTH   | UNITS | BILL (PKR) | PAYMENT  || MONTH   | UNITS | BILL (PKR) | ... |
| SEP 25  | 286   | 10899      | PAID     || MAR 26  | 191   | 8887       | ... |
| OCT 25  | 262   | 10842      | PAID     || APR 26  | 246   | 12352      | ... |
| NOV 25  | 193   | 18836      | PAID     || MAY 26  | 261   | 12697      | ... |
| DEC 25  | 157   | 5806       | PAID     || JUN 26  | 314   | 16278      | ... |
| JAN 26  | 203   | 8695       | PAID     || JUL 26  | 414   | 21791      | ... |
| FEB 26  | 182   | 16842      | PAID     || AUG 26  | 339   | 16997      | ... |
+-------------------------------------------------------------------------------+
| CURRENT MONTH: SEP 26  | UNITS: 339    | TOTAL PAYABLE: Rs 16,997             |
+-------------------------------------------------------------------------------+
```

### 3. Key Parsing Targets & Robust Regex Patterns

#### A. Reference Number (14 digits + RU Code):
PITC bills print reference numbers with varying spacing:
- Patterns: `14 13435 2211500 R`, `14134352211500R`, `14-13435-2211500-U`, `14 13435 2211500`
- Regex:
  ```python
  re.search(r"(?:REF(?:ERENCE)?\s*(?:NO|NUMBER)?[:\s]*)?([0-9]{2}[\s\-]?[0-9]{5}[\s\-]?[0-9]{7}[\s\-]?[A-Z]?)", text, re.IGNORECASE)
  ```

#### B. Consumer Name & Address:
- Name usually follows `NAME`, `NAME & ADDRESS`, or `CONSUMER NAME`.
- Address follows `ADDRESS` or sits directly below the consumer's name block.

#### C. Sanctioned Load:
- Patterns: `SANCTIONED LOAD: 3.00 KW`, `LOAD: 5 KW`, `LOAD (KW): 7.0`
- Regex:
  ```python
  re.search(r"(?:SANCTIONED\s*LOAD|LOAD)\s*[:\s]*([0-9]+(?:\.[0-9]+)?)\s*(?:KW|K\.W)", text, re.IGNORECASE)
  ```

#### D. Tariff:
- Patterns: `TARIFF: A-1a(01)`, `A-1A`, `A-2A`, `A-1a(02)`
- Regex:
  ```python
  re.search(r"TARIFF\s*[:\s]*([A-Z0-9\-\(\)]+)", text, re.IGNORECASE)
  ```

#### E. 12-Month Billing History:
PITC bills frequently format history in **two parallel columns of 6 months** or in a grid table:
- Month format: 3-letter month abbreviation (`JAN`, `FEB`, `MAR`, `APR`, `MAY`, `JUN`, `JUL`, `AUG`, `SEP`, `OCT`, `NOV`, `DEC`) followed by 2-digit year (e.g. `SEP25`, `SEP 25`, `SEP-25`).
- Columns per month: `Units` (integer `50–3000`), `Bill Amount / Payable` (float/int `1,000–500,000`).
- Extraction must support:
  1. Horizontal table parsing (via `pypdf` lines or `pdfplumber.extract_tables()`).
  2. Multi-column text scanning (e.g. `SEP25 286 10899 MAR26 191 8887`).

---

## 🛠️ Step-by-Step Implementation Instructions

### Step 1: Create Custom Exception Class
In `src/fesco_solar/extractors/base.py`:
```python
class PdfExtractionError(Exception):
    """Raised when a PDF bill cannot be parsed or lacks critical billing fields."""
    def __init__(self, message: str, missing_fields: list[str], raw_text_preview: str = ""):
        super().__init__(message)
        self.missing_fields = missing_fields
        self.raw_text_preview = raw_text_preview
```

### Step 2: Implement Real Two-Pass PDF Extraction in `pdf_parser.py`
```python
class PdfBillExtractor(BaseBillExtractor):
    """Production-grade PDF bill extractor with zero synthetic fallbacks."""

    def extract(self, pdf_path: str) -> ElectricityBill:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")

        # 1. Read raw text and tables
        raw_text, tables = self._read_pdf(pdf_path)
        if not raw_text.strip():
            raise PdfExtractionError(
                message="The provided PDF contains no readable text streams. If this is a scanned photo or image, OCR is required.",
                missing_fields=["all_text_streams"],
                raw_text_preview=""
            )

        # 2. Extract mandatory fields
        ref_no = self._extract_reference_number(raw_text)
        sanctioned_load = self._extract_sanctioned_load(raw_text)
        tariff_code = self._extract_tariff_code(raw_text)
        consumer_name = self._extract_consumer_name(raw_text)
        address = self._extract_address(raw_text)
        history = self._extract_billing_history(raw_text, tables)

        # 3. Validate mandatory fields (STRICT: NO DUMMY DATA)
        missing = []
        if not ref_no:
            missing.append("reference_number")
        if not sanctioned_load:
            missing.append("sanctioned_load")
        if not history or len(history) < 1:
            missing.append("billing_history")

        if missing:
            snippet = raw_text[:500] if len(raw_text) > 500 else raw_text
            raise PdfExtractionError(
                message=f"Failed to extract mandatory bill fields: {', '.join(missing)}. Please verify this is a valid FESCO computerized bill.",
                missing_fields=missing,
                raw_text_preview=snippet,
            )

        # Build genuine ElectricityBill model
        ...
```

### Step 3: Scanned PDF / Image Detection
Add detection for image-only PDFs:
- If `len(raw_text.strip()) < 50` and the file has PDF pages, flag that the PDF is an image scan.
- Return a clear error message instructing the user:
  > *"This PDF appears to be a scanned image or photo without selectable text. Please provide a computerized PDF bill, or use the 14-digit reference number with `--ref` to fetch the bill directly from the online portal."*

### Step 4: Add Unit Tests for Strict Validation
In `tests/test_extractors.py`:
- Test valid PDF extraction verifies all extracted fields match the source file.
- Test invalid/corrupted PDF raises `PdfExtractionError` instead of returning fake data.
- Test empty text PDF raises `PdfExtractionError` with missing fields list.

---

## 📋 Verification Checklist
- [ ] No occurrences of `"13131241234567U"` in `pdf_parser.py`.
- [ ] No synthetic history multiplier loop (`base_u * w`).
- [ ] Running on a malformed PDF raises `PdfExtractionError` with helpful error diagnostics.
- [ ] Running on a real FESCO computerized PDF extracts authentic consumer name, reference number, load, tariff, and 12-month records.
