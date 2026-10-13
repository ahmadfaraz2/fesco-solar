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
    def parse_sanctioned_load(text: str, default_kw: float = 5.0) -> float:
        """Find sanctioned load (kW) using robust regex heuristics."""
        patterns = [
            r"SANCTIONED\s*LOAD[\s:]*([0-9]+(?:\.[0-9]+)?)\s*(?:KW)?",
            r"LOAD[\s:]*([0-9]+(?:\.[0-9]+)?)\s*KW",
            r"S\.?LOAD[\s:]*([0-9]+(?:\.[0-9]+)?)\s*(?:KW)?",
            r"SANC\s*LOAD[\s:]*([0-9]+(?:\.[0-9]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    if 0.5 <= val <= 200.0:
                        return val
                except (ValueError, IndexError):
                    continue
        return default_kw

    @staticmethod
    def parse_tariff_code(text: str, default: str = "A-1a(01)") -> str:
        """Find tariff classification code from text."""
        match = re.search(r"TARIFF[\s:]*([A-Z0-9\-\(\)]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default
