"""Unit tests for online and PDF bill extractors."""

from __future__ import annotations

import os
import pytest
from pypdf import PdfWriter

from fesco_solar.extractors.base import PdfExtractionError, PitcPortalError
from fesco_solar.extractors.pdf_parser import PdfBillExtractor
from fesco_solar.extractors.pitc_online import PitcOnlineExtractor


def test_pitc_extractor_live_fetch():
    """Test online extractor queries live PITC portal when TEST_FESCO_REF is configured."""
    test_ref = os.environ.get("TEST_FESCO_REF")
    if not test_ref:
        pytest.skip("TEST_FESCO_REF not configured in environment (protects personal data)")

    extractor = PitcOnlineExtractor()
    try:
        bill = extractor.extract(test_ref)
        assert len(bill.consumer.reference_number) >= 14
        assert len(bill.history) >= 1
        assert bill.tariff.sanctioned_load_kw > 0
    except PitcPortalError:
        pytest.skip("PITC billing portal is currently unreachable or timed out")


def test_pitc_extractor_fake_ref_raises_error():
    """Verify that a non-existent reference strictly raises PitcPortalError (zero dummy fallback policy)."""
    extractor = PitcOnlineExtractor()
    with pytest.raises(PitcPortalError):
        extractor.extract("99999999999999")


def test_pitc_extractor_invalid_short_ref():
    """Test extractor raises error on invalid reference number length."""
    extractor = PitcOnlineExtractor()
    with pytest.raises(ValueError):
        extractor.extract("12345")


def test_pdf_extractor_nonexistent_file():
    """Test that missing PDF raises FileNotFoundError."""
    extractor = PdfBillExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract("non_existent_bill.pdf")


def test_pdf_extractor_sample_bill():
    """Test genuine extraction from data/sample_fesco_bill.pdf."""
    sample_path = os.path.join("data", "sample_fesco_bill.pdf")
    assert os.path.exists(sample_path), "Sample bill PDF must exist"

    extractor = PdfBillExtractor()
    bill = extractor.extract(sample_path)

    assert bill.consumer.reference_number == "13131241234567U"
    assert bill.consumer.consumer_name == "HAJI ABDUL WAHEED"
    assert "FAISALABAD" in bill.consumer.address.upper()
    assert bill.tariff.sanctioned_load_kw == 7.0
    assert bill.tariff.phase_type == "3-Phase"
    assert bill.tariff.tariff_code == "A-1a(01)"
    assert len(bill.history) == 12
    assert bill.current_bill_pkr == 35360.0
    assert bill.current_units == 680


def test_pdf_extractor_local_bill():
    """Test genuine extraction from local bill.pdf if present without hardcoding PII."""
    bill_path = "bill.pdf"
    if not os.path.exists(bill_path):
        pytest.skip("bill.pdf not present in test environment")

    extractor = PdfBillExtractor()
    bill = extractor.extract(bill_path)

    # Validate structural fields genuinely extracted without exposing personal identity
    assert len(bill.consumer.reference_number) >= 14
    assert bill.consumer.consumer_name and bill.consumer.consumer_name != "N/A"
    assert bill.tariff.sanctioned_load_kw > 0
    assert bill.tariff.phase_type in ("1-Phase", "3-Phase")
    assert len(bill.history) == 12
    assert bill.current_bill_pkr > 0


def test_pdf_extractor_empty_scanned_pdf(tmp_path):
    """Test scanned / image-only PDF detection raises PdfExtractionError."""
    empty_pdf_path = tmp_path / "scanned_empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(empty_pdf_path, "wb") as f:
        writer.write(f)

    extractor = PdfBillExtractor()
    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(str(empty_pdf_path))

    assert "scanned image" in str(exc_info.value).lower()
    assert "all_text_streams" in exc_info.value.missing_fields


def test_pdf_extractor_missing_mandatory_fields(tmp_path):
    """Test arbitrary document with readable text but lacking bill fields raises error."""
    invalid_pdf_path = tmp_path / "not_a_bill.pdf"
    # Create a minimal PDF containing arbitrary non-bill text
    content = "Hello, this is a generic document with selectable text but completely lacking any bill fields."
    stream_data = f"BT /F1 12 Tf 50 750 Td ({content}) Tj ET"
    stream_len = len(stream_data)
    pdf_bytes = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length {stream_len} >> stream
{stream_data}
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000301 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
{stream_len + 360}
%%EOF""".encode("latin1")

    with open(invalid_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    extractor = PdfBillExtractor()
    with pytest.raises(PdfExtractionError) as exc_info:
        extractor.extract(str(invalid_pdf_path))

    assert "mandatory bill fields" in str(exc_info.value).lower()
    assert "reference_number" in exc_info.value.missing_fields
    assert "sanctioned_load" in exc_info.value.missing_fields
    assert "billing_history" in exc_info.value.missing_fields
