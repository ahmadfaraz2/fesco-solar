"""Unit tests for bill extractors."""

from __future__ import annotations

import pytest
from fesco_solar.extractors.pitc_online import PitcOnlineExtractor
from fesco_solar.extractors.pdf_parser import PdfBillExtractor


def test_pitc_extractor_valid_14_digit():
    """Test online extractor with valid 14-digit reference number."""
    extractor = PitcOnlineExtractor()
    bill = extractor.extract("13 13124 1234567 U")

    assert bill.consumer.reference_number == "13131241234567U"
    assert len(bill.history) >= 12
    assert bill.tariff.sanctioned_load_kw > 0
    assert bill.total_annual_units > 0


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
