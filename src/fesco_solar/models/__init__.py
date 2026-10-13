"""Data models package for fesco-solar."""

from fesco_solar.models.bill import (
    ConsumerDetails,
    ElectricityBill,
    MonthlyRecord,
    TariffInfo,
)
from fesco_solar.models.solar import (
    PunjabSolarProfile,
    SolarPanelSpec,
    SystemRecommendation,
    SystemType,
)
from fesco_solar.models.pricing import (
    RatesCache,
    SolarPlateRate,
    TurnkeyBOSCost,
)
from fesco_solar.models.financial import FinancialSummary

__all__ = [
    "ConsumerDetails",
    "ElectricityBill",
    "MonthlyRecord",
    "TariffInfo",
    "PunjabSolarProfile",
    "SolarPanelSpec",
    "SystemRecommendation",
    "SystemType",
    "RatesCache",
    "SolarPlateRate",
    "TurnkeyBOSCost",
    "FinancialSummary",
]
