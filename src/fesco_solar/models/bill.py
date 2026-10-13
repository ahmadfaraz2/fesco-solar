"""Pydantic v2 data models for FESCO / PITC electricity bills."""

from __future__ import annotations
import re
from typing import List, Optional

try:
    from pydantic import BaseModel, Field, computed_field, field_validator
except ImportError:
    from fesco_solar.models.compat import BaseModel, Field, computed_field, field_validator


class MonthlyRecord(BaseModel):
    """Monthly electricity consumption and billing record."""

    month_name: str = Field(description="Month and year e.g. JAN-24, 2024-01, or Jan")
    units_consumed: int = Field(ge=0, description="Total units (kWh) consumed in the month")
    bill_amount_pkr: float = Field(ge=0.0, description="Total billed amount in PKR")
    peak_units: Optional[int] = Field(default=None, ge=0, description="Peak hours units if applicable (TOU meters)")
    off_peak_units: Optional[int] = Field(default=None, ge=0, description="Off-peak hours units if applicable")
    payment_status: Optional[str] = Field(default="PAID", description="Payment status (PAID/UNPAID)")


class TariffInfo(BaseModel):
    """Tariff and connection specifications for the consumer."""

    tariff_code: str = Field(default="A-1a(01)", description="Tariff category code, e.g., A-1a (Domestic), A-2a (Commercial)")
    sanctioned_load_kw: float = Field(default=5.0, ge=0.1, description="Sanctioned load approved by FESCO in kW")
    meter_number: Optional[str] = Field(default=None, description="Physical electric meter number")
    feeder_name: Optional[str] = Field(default=None, description="Grid feeder name e.g. City-1, Millat Town")
    connection_date: Optional[str] = Field(default=None, description="Date of original electricity connection")
    phase_type: str = Field(default="3-Phase", description="1-Phase or 3-Phase connection")


class ConsumerDetails(BaseModel):
    """Consumer identification and location information."""

    reference_number: str = Field(description="14-digit FESCO reference number (may include check alphabet)")
    consumer_name: str = Field(default="Valued Consumer", description="Registered consumer name on bill")
    address: str = Field(default="Faisalabad Region, Punjab", description="Consumer physical premises address")
    cnic: Optional[str] = Field(default=None, description="CNIC of consumer if available on bill")
    sub_division: Optional[str] = Field(default=None, description="FESCO Sub-Division office name")

    @field_validator("reference_number")
    @classmethod
    def clean_reference_number(cls, v: str) -> str:
        cleaned = re.sub(r"\s+", "", v.strip().upper())
        if len(re.sub(r"[^0-9]", "", cleaned)) < 14:
            raise ValueError(f"Reference number must contain at least 14 digits, got: {v}")
        return cleaned


class ElectricityBill(BaseModel):
    """Aggregated electricity bill representing 12-month profile and current status."""

    consumer: ConsumerDetails
    tariff: TariffInfo
    bill_month: str = Field(default="CURRENT", description="Billing month of this invoice")
    issue_date: Optional[str] = Field(default=None, description="Bill issue date")
    due_date: Optional[str] = Field(default=None, description="Payment due date")
    current_units: int = Field(ge=0, description="Current month units consumed")
    current_bill_pkr: float = Field(ge=0.0, description="Current month payable amount in PKR")
    history: List[MonthlyRecord] = Field(default_factory=list, description="Historical monthly records (up to 12 months)")

    @computed_field
    @property
    def total_annual_units(self) -> int:
        """Total units consumed over the available billing history."""
        if not self.history:
            return self.current_units * 12
        return sum(record.units_consumed for record in self.history)

    @computed_field
    @property
    def average_monthly_units(self) -> float:
        """Average monthly electricity consumption in kWh."""
        if not self.history:
            return float(self.current_units)
        return round(sum(record.units_consumed for record in self.history) / len(self.history), 1)

    @computed_field
    @property
    def peak_summer_units(self) -> int:
        """Maximum monthly units during high-summer (May to September or peak historical record)."""
        if not self.history:
            return int(self.current_units * 1.4)
        return max(record.units_consumed for record in self.history)

    @computed_field
    @property
    def winter_minimum_units(self) -> int:
        """Minimum monthly units during winter (typically December to February)."""
        if not self.history:
            return int(self.current_units * 0.5)
        return min(record.units_consumed for record in self.history)

    @computed_field
    @property
    def seasonal_swing_ratio(self) -> float:
        """Ratio of peak summer consumption to winter minimum consumption."""
        min_u = max(1, self.winter_minimum_units)
        return round(self.peak_summer_units / min_u, 2)
