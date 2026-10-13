"""Base class and common parsing utilities for FESCO bill extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Dict, List, Optional

from fesco_solar.models.bill import (
    ConsumerDetails,
    ElectricityBill,
    MonthlyRecord,
    TariffInfo,
)


class PdfExtractionError(Exception):
    """Raised when a PDF bill cannot be parsed or lacks critical billing fields."""

    def __init__(
        self,
        message: str,
        missing_fields: Optional[List[str]] = None,
        raw_text_preview: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.missing_fields = missing_fields or []
        self.raw_text_preview = raw_text_preview

    def __str__(self) -> str:
        return self.message


class PitcPortalError(Exception):
    """Raised when the online PITC billing portal cannot retrieve a genuine bill."""

    def __init__(self, message: str, reference_number: str = ""):
        super().__init__(message)
        self.message = message
        self.reference_number = reference_number

    def __str__(self) -> str:
        return self.message


class BaseBillExtractor(ABC):
    """Abstract base extractor interface for electricity bills."""

    @abstractmethod
    def extract(self, source: str) -> ElectricityBill:
        """Extract and parse an ElectricityBill model from given input source."""
        pass

    @staticmethod
    def clean_ref_number(raw_ref: str) -> str:
        """Strip spaces, hyphens, and normalize 14-digit reference number."""
        clean = re.sub(r"[\s\-_]+", "", raw_ref.strip().upper())
        return clean

    @staticmethod
    def parse_sanctioned_load(text: str, default_kw: Optional[float] = None) -> Optional[float]:
        """Find sanctioned load (kW) using robust regex heuristics."""
        patterns = [
            r"(?:SANCTIONED\s*LOAD|SAN\s*LOAD|SANC\s*LOAD|S\.?\s*LOAD|LOAD)[\s\:\-\u0600-\u06FF]*\n?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:KW|K\.W)?\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    if 0.1 <= val <= 500.0:
                        return val
                except (ValueError, IndexError):
                    continue
        return default_kw

    @staticmethod
    def parse_tariff_code(text: str, default: Optional[str] = None) -> Optional[str]:
        """Find tariff classification code from text, excluding TARIFF CATEGORY."""
        # First match specific TARIFF code like A-1A(01)
        match = re.search(r"(?<!CATEGORY\s)TARIFF(?!\s*CATEGORY)[\s\:\-\u0600-\u06FF]*\n?\s*([A-Za-z][0-9A-Za-z\-\(\)]+)", text, re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # If code captured is just 'CATEGORY', ignore it
            if code.upper() != "CATEGORY":
                return code

        # General tariff code regex
        gen_match = re.search(r"\b([A-Z]-[0-9][a-zA-Z]?(?:\([0-9]+\))?)\b", text)
        if gen_match:
            return gen_match.group(1).strip()

        return default

