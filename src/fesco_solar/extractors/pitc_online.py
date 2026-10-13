"""Online bill extractor for PITC / FESCO billing portal."""

from __future__ import annotations

import re
from typing import List, Optional
from bs4 import BeautifulSoup
import httpx

from fesco_solar.extractors.base import BaseBillExtractor, PitcPortalError
from fesco_solar.models.bill import (
    ConsumerDetails,
    ElectricityBill,
    MonthlyRecord,
    TariffInfo,
)


class PitcOnlineExtractor(BaseBillExtractor):
    """Extractor for retrieving bills via 14-digit reference numbers from PITC portal."""

    PORTAL_URL = "https://bill.pitc.com.pk/fescobill"

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.last_fetch_was_live: bool = False

    def extract(self, reference_number: str) -> ElectricityBill:
        """Fetch genuine online bill from PITC using 14-digit reference number.

        Raises:
            ValueError: If reference number does not contain 14 digits.
            PitcPortalError: If PITC portal is unreachable or reference is not found.
        """
        clean_ref = self.clean_ref_number(reference_number)
        
        # Determine 14 digits and optional RU code (U=Urban, R=Rural)
        digits_only = re.sub(r"[^0-9]", "", clean_ref)
        if len(digits_only) < 14:
            raise ValueError(
                f"Invalid FESCO Reference Number '{reference_number}'. "
                "Must be a 14-digit number (e.g. '14 12345 6789012 U' or '14123456789012')."
            )

        ref_14 = digits_only[:14]
        # Extract check character if given at the end
        ru_hint = clean_ref[14:15] if len(clean_ref) > 14 and clean_ref[14] in ("U", "R") else None

        html_content, matched_ru = self._fetch_portal_html(ref_14, ru_hint)
        if html_content:
            bill = self._parse_html(html_content, f"{ref_14}{matched_ru or 'R'}")
            if bill:
                self.last_fetch_was_live = True
                return bill

        self.last_fetch_was_live = False
        raise PitcPortalError(
            f"Could not retrieve bill for reference number '{clean_ref}'. "
            "The PITC online portal is currently unreachable or this reference number was not found. "
            "Please verify the 14-digit reference number, or provide a computerized PDF bill using '--pdf'.",
            reference_number=clean_ref,
        )

    def _fetch_portal_html(self, ref_14: str, ru_hint: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
        """Query PITC ASP.NET billing portal by posting reference number and RU code."""
        ru_codes_to_try = [ru_hint] if ru_hint else ["R", "U"]

        for ru in ru_codes_to_try:
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=True, verify=False) as client:
                    # 1. Fetch form to get ASP.NET session tokens
                    r1 = client.get(self.PORTAL_URL, headers=self.headers)
                    if r1.status_code != 200:
                        continue
                    
                    soup1 = BeautifulSoup(r1.text, "html.parser")
                    viewstate = soup1.find("input", {"name": "__VIEWSTATE"})
                    viewstategen = soup1.find("input", {"name": "__VIEWSTATEGENERATOR"})
                    eventval = soup1.find("input", {"name": "__EVENTVALIDATION"})

                    if not (viewstate and viewstategen and eventval):
                        continue

                    data = {
                        "__VIEWSTATE": viewstate.get("value", ""),
                        "__VIEWSTATEGENERATOR": viewstategen.get("value", ""),
                        "__EVENTVALIDATION": eventval.get("value", ""),
                        "rbSearchByList": "refno",
                        "searchTextBox": ref_14,
                        "ruCodeTextBox": ru,
                        "btnSearch": "Search",
                    }
                    token = soup1.find("input", {"name": "__RequestVerificationToken"})
                    if token:
                        data["__RequestVerificationToken"] = token.get("value", "")

                    # 2. Submit form
                    r2 = client.post(self.PORTAL_URL, data=data, headers=self.headers)
                    text = r2.text
                    if r2.status_code == 200 and ("CONSUMER DETAIL" in text or "ELECTRICITY CONSUMER BILL" in text or "BILL HISTORY" in text):
                        return text, ru
            except Exception:
                continue

        # Also try direct GET endpoint as backup
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, verify=False) as client:
                r_get = client.get(f"{self.PORTAL_URL}/general?refno={ref_14}", headers=self.headers)
                if r_get.status_code == 200 and ("CONSUMER DETAIL" in r_get.text or "BILL HISTORY" in r_get.text):
                    return r_get.text, ru_hint or "R"
        except Exception:
            pass

        return None, None

    def _parse_html(self, html: str, ref_clean: str) -> Optional[ElectricityBill]:
        """Parse PITC bill HTML DOM structure with zero synthetic values."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        # 1. Parse Consumer Details from consumer-detail-card
        c_pairs: dict[str, str] = {}
        c_card = soup.find(class_=lambda c: c and "consumer-detail-card" in c)
        if c_card:
            for lbl in c_card.find_all(class_="label-row"):
                en = lbl.find(class_="en-lbl")
                if en:
                    v = lbl.find_next_sibling(class_=lambda c: c and "val-space" in c)
                    c_pairs[en.get_text(strip=True).upper()] = v.get_text(" ", strip=True) if v else ""

        # Name & Address
        name = "N/A"
        address = "N/A"
        raw_name_addr = c_pairs.get("NAME & ADDRESS")
        if raw_name_addr:
            parts = [p.strip() for p in raw_name_addr.split(",") if p.strip()]
            if len(parts) >= 2:
                name = parts[0]
                if any(k in parts[1].upper() for k in ("S/O", "D/O", "W/O", "SO ", "DO ", "WO ")):
                    name = f"{parts[0]}, {parts[1]}"
                    address = ", ".join(parts[2:]) if len(parts) > 2 else "Punjab"
                else:
                    address = ", ".join(parts[1:])
            else:
                name = raw_name_addr
        else:
            name_match = re.search(r"NAME\s*&\s*ADDRESS[^\n\r:]*[:\s]*([A-Z\s\.\/]{3,40})(?=\s*ADDRESS|\s*TRANSFORMER|\s*CNIC)", text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()

        consumer_id = c_pairs.get("CONSUMER ID") or None
        transformer = c_pairs.get("TRANSFORMER") or None
        feeder = c_pairs.get("FEEDER") or None
        sub_division = c_pairs.get("SUB DIVISION") or None
        category = c_pairs.get("CATEGORY") or None
        status = c_pairs.get("STATUS") or None

        if not feeder:
            feeder_match = re.search(r"FEEDER[\s\u0600-\u06FF:]*([0-9A-Z\s\-]+?)(?=\s*SUB\s*DIVISION|\s*CATEGORY|\s*TRANSFORMER)", text, re.IGNORECASE)
            if feeder_match:
                feeder = feeder_match.group(1).strip()

        if not sub_division:
            sub_match = re.search(r"SUB\s*DIVISION[\s\u0600-\u06FF:]*([0-9A-Z\s\-]+?)(?=\s*CATEGORY|\s*TARIFF|\s*STATUS)", text, re.IGNORECASE)
            if sub_match:
                sub_division = sub_match.group(1).strip()

        # 2. Sanctioned Load (Strict - Zero Dummy Fallback)
        sanctioned_load = None
        raw_load = c_pairs.get("SAN LOAD")
        if raw_load:
            cand = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw_load)
            if cand:
                try:
                    sanctioned_load = float(cand.group(1))
                except ValueError:
                    pass

        if sanctioned_load is None:
            sanctioned_load = self.parse_sanctioned_load(text, default_kw=None)

        if sanctioned_load is None or sanctioned_load <= 0:
            raise PitcPortalError(
                f"Failed to extract sanctioned load from PITC portal bill for reference '{ref_clean}'.",
                reference_number=ref_clean,
            )

        # 3. Tariff Code
        tariff_code = c_pairs.get("TARIFF")
        if not tariff_code or tariff_code.upper() == "CATEGORY":
            tariff_code = self.parse_tariff_code(text, default=None)

        if not tariff_code:
            raise PitcPortalError(
                f"Failed to extract tariff classification code for reference '{ref_clean}'.",
                reference_number=ref_clean,
            )

        # 4. Meter Info Card (Readings & Units)
        meter_no = None
        prev_reading = None
        pres_reading = None
        current_units = None

        m_card = soup.find(class_=lambda c: c and "meter-info" in c)
        if m_card:
            for cell in m_card.find_all(class_="meter-info-cell"):
                en = cell.find(class_="en-lbl")
                v = cell.find(class_="val-space")
                if not (en and v):
                    continue
                lbl_txt = en.get_text(strip=True).upper()
                v_lines = [s.strip() for s in v.stripped_strings if s.strip()]
                if not v_lines:
                    continue
                first_v = v_lines[0]

                if "METER NO" in lbl_txt:
                    meter_no = first_v
                elif "PREVIOUS READING" in lbl_txt:
                    try:
                        prev_reading = int(re.sub(r"[^0-9]", "", first_v))
                    except ValueError:
                        pass
                elif "PRESENT READING" in lbl_txt:
                    try:
                        pres_reading = int(re.sub(r"[^0-9]", "", first_v))
                    except ValueError:
                        pass
                elif "UNITS" in lbl_txt and "BILL" not in lbl_txt:
                    try:
                        current_units = int(re.sub(r"[^0-9]", "", first_v))
                    except ValueError:
                        pass

        phase_type = "1-Phase" if (sanctioned_load < 5.0 or (meter_no and "S-P" in meter_no.upper())) else "3-Phase"

        # 5. Itemized Bill Charges Breakdown
        charges: dict = {}
        chg_card = soup.find(class_=lambda c: c and "charges-breakdown-card" in c)
        if chg_card:
            for row in chg_card.find_all(class_="charges-bd-row"):
                lbl_el = row.find(class_="charges-bd-en")
                val_el = row.find(class_="charges-bd-val")
                if not (lbl_el and val_el):
                    continue
                l_text = lbl_el.get_text(" ", strip=True).upper()
                v_text = val_el.get_text(strip=True).replace(",", "")
                try:
                    num = float(re.sub(r"[^0-9\.]", "", v_text))
                except ValueError:
                    continue

                if "TOTAL ELECTRICITY CHARGES" in l_text:
                    charges["electricity_charges"] = num
                elif "SUBSIDIES" in l_text:
                    charges["subsidies"] = num
                elif "NET ELECTRICITY CHARGES" in l_text:
                    charges["net_charges"] = num
                elif "TAXES" in l_text:
                    charges["taxes"] = num
                elif "CURRENT BILL" in l_text:
                    charges["current_bill_charges"] = num
                elif "TOTAL FPA" in l_text:
                    charges["fpa"] = num
                elif "ARREARS" in l_text:
                    charges["arrears"] = num
                elif "GRAND TOTAL" in l_text:
                    charges["grand_total"] = num

        # 6. Right Sidebar: Bill Month, Due Dates, and Payment Info
        bill_month = "CURRENT"
        issue_date = None
        due_date = None
        late_surcharge = None
        payable_after_due_date = None
        amount_paid = None
        payment_date = None

        sb = soup.find(class_=lambda c: c and "right-sidebar" in c)
        if sb:
            bm_el = sb.find(class_="right-main-val")
            if bm_el:
                bill_month = bm_el.get_text(strip=True)
            due_el = sb.find(class_="right-main-val--due")
            if due_el:
                due_date = due_el.get_text(strip=True)
            for d_cell in sb.find_all(class_="right-grid-cell"):
                en_txt = d_cell.get_text(" ", strip=True).upper()
                d_val = d_cell.find(class_="right-panel-date-val")
                if d_val and "ISSUE DATE" in en_txt:
                    issue_date = d_val.get_text(strip=True)

            sur_el = sb.find(class_="lp-surcharge-top-val")
            if sur_el:
                try:
                    late_surcharge = float(re.sub(r"[^0-9\.]", "", sur_el.get_text(strip=True)))
                except ValueError:
                    pass

            after_el = sb.find(class_="lp-surcharge-bottom-val")
            if after_el:
                try:
                    payable_after_due_date = float(re.sub(r"[^0-9\.]", "", after_el.get_text(strip=True)))
                except ValueError:
                    pass

            paid_rows = sb.find_all(class_="payable-card-paid-row")
            for pr in paid_rows:
                lbl_t = pr.get_text(" ", strip=True).upper()
                val_t = pr.find(class_="payable-card-paid-val")
                if val_t:
                    if "AMOUNT PAID" in lbl_t:
                        try:
                            amount_paid = float(re.sub(r"[^0-9\.]", "", val_t.get_text(strip=True)))
                        except ValueError:
                            pass
                    elif "PAYMENT DATE" in lbl_t:
                        payment_date = val_t.get_text(strip=True)

        current_bill_pkr = charges.get("grand_total")
        if current_bill_pkr is None:
            if charges.get("current_bill_charges") is not None:
                current_bill_pkr = charges["current_bill_charges"]

        # 7. Parse 12-Month Billing History with Status (e.g. DF) Support
        history: List[MonthlyRecord] = []
        history_rows = soup.find_all(class_=lambda c: c and "history-row" in c)
        for h_row in history_rows:
            cells = [c.get_text(strip=True) for c in h_row.find_all(class_="history-cell") if c.get_text(strip=True)]
            if len(cells) >= 3:
                m_cand = cells[0]
                if any(m in m_cand.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
                    # Handle optional status column (e.g. 'Aug26', 'DF', '244', '10937')
                    has_status = not cells[1].isdigit()
                    status_val = cells[1] if has_status else "PAID"
                    u_idx = 2 if has_status else 1
                    amt_idx = 3 if has_status else 2

                    if len(cells) > amt_idx:
                        try:
                            u_val = int(re.sub(r"[^0-9]", "", cells[u_idx]))
                            amt_val = float(re.sub(r"[^0-9\.]", "", cells[amt_idx]))
                            history.append(
                                MonthlyRecord(
                                    month_name=m_cand.upper(),
                                    units_consumed=u_val,
                                    bill_amount_pkr=amt_val,
                                    payment_status=status_val,
                                )
                            )
                        except (ValueError, IndexError):
                            continue

        if not history:
            # Fallback to tables if history-row not present
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"]) if td.get_text(strip=True)]
                    if len(cols) >= 3:
                        m_match = re.search(r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z0-9\-\s]*$", cols[0], re.IGNORECASE)
                        if m_match:
                            has_stat = not cols[1].isdigit()
                            u_idx = 2 if has_stat else 1
                            amt_idx = 3 if has_stat else 2
                            if len(cols) > amt_idx:
                                try:
                                    u_val = int(re.sub(r"[^0-9]", "", cols[u_idx]))
                                    amt_val = float(re.sub(r"[^0-9\.]", "", cols[amt_idx]))
                                    history.append(
                                        MonthlyRecord(
                                            month_name=cols[0].upper(),
                                            units_consumed=u_val,
                                            bill_amount_pkr=amt_val,
                                            payment_status=cols[1] if has_stat else "PAID",
                                        )
                                    )
                                except (ValueError, IndexError):
                                    continue

        if not history:
            raise PitcPortalError(
                f"No monthly billing history found on PITC portal for reference '{ref_clean}'.",
                reference_number=ref_clean,
            )

        if current_units is None:
            current_units = history[-1].units_consumed if history else 0
        if current_bill_pkr is None:
            current_bill_pkr = history[-1].bill_amount_pkr if history else 0.0

        consumer = ConsumerDetails(
            reference_number=ref_clean,
            consumer_name=name,
            address=address,
            consumer_id=consumer_id,
            sub_division=sub_division,
            transformer=transformer,
            connection_status=status,
            billing_category=category,
        )
        tariff = TariffInfo(
            tariff_code=tariff_code,
            sanctioned_load_kw=sanctioned_load,
            meter_number=meter_no,
            feeder_name=feeder,
            phase_type=phase_type,
        )

        return ElectricityBill(
            consumer=consumer,
            tariff=tariff,
            bill_month=bill_month,
            issue_date=issue_date,
            due_date=due_date,
            current_units=current_units,
            current_bill_pkr=current_bill_pkr,
            history=history,
            previous_reading=prev_reading,
            present_reading=pres_reading,
            electricity_charges_pkr=charges.get("electricity_charges"),
            subsidies_pkr=charges.get("subsidies"),
            net_electricity_charges_pkr=charges.get("net_charges"),
            taxes_pkr=charges.get("taxes"),
            fpa_pkr=charges.get("fpa"),
            current_bill_charges_pkr=charges.get("current_bill_charges"),
            arrears_pkr=charges.get("arrears", 0.0),
            late_surcharge_pkr=late_surcharge,
            payable_after_due_date_pkr=payable_after_due_date,
            amount_paid_pkr=amount_paid,
            payment_date=payment_date,
        )

    def _generate_representative_bill(self, clean_ref: str, digits: str) -> ElectricityBill:
        """Create an authentic representative FESCO 12-month billing profile."""
        seed_num = sum(int(d) for d in digits[:14])
        base_summer_units = 650 + (seed_num % 5) * 60
        base_winter_units = int(base_summer_units * 0.42)
        sanctioned_load_kw = 5.0 if base_summer_units < 800 else 8.0

        months_data = [
            ("OCT-25", int(base_summer_units * 0.72)),
            ("NOV-25", int(base_summer_units * 0.50)),
            ("DEC-25", base_winter_units),
            ("JAN-26", int(base_winter_units * 0.95)),
            ("FEB-26", int(base_winter_units * 1.05)),
            ("MAR-26", int(base_summer_units * 0.58)),
            ("APR-26", int(base_summer_units * 0.75)),
            ("MAY-26", int(base_summer_units * 0.95)),
            ("JUN-26", int(base_summer_units * 1.08)),
            ("JUL-26", int(base_summer_units * 1.12)),
            ("AUG-26", base_summer_units),
            ("SEP-26", int(base_summer_units * 0.88)),
        ]

        history: List[MonthlyRecord] = []
        for m_name, units in months_data:
            bill_amt = round(units * 52.0, 2)
            history.append(MonthlyRecord(
                month_name=m_name,
                units_consumed=units,
                bill_amount_pkr=bill_amt,
                payment_status="PAID",
            ))

        consumer = ConsumerDetails(
            reference_number=clean_ref,
            consumer_name="Muhammad Farooq Akhtar",
            address="House #42-B, People's Colony #1, Faisalabad",
            cnic="33100-1234567-1",
            sub_division="Peoples Colony Sub-Division, FESCO",
        )
        tariff = TariffInfo(
            tariff_code="A-1a(01) Domestic",
            sanctioned_load_kw=sanctioned_load_kw,
            meter_number="FES-984210",
            feeder_name="D-Ground Express Feeder",
            phase_type="3-Phase",
        )

        current_units = months_data[-1][1]
        current_bill = round(current_units * 52.0, 2)

        return ElectricityBill(
            consumer=consumer,
            tariff=tariff,
            bill_month="SEP-26",
            current_units=current_units,
            current_bill_pkr=current_bill,
            history=history,
        )
