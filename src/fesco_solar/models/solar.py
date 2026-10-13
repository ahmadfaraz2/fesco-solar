"""Pydantic v2 data models for solar sizing, irradiance, and system recommendations."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
try:
    from pydantic import BaseModel, Field, computed_field
except ImportError:
    from fesco_solar.models.compat import BaseModel, Field, computed_field


class SystemType(str, Enum):
    """Solar system architecture."""

    ON_GRID = "On-Grid (Net Metered)"
    HYBRID = "Hybrid (Battery Backup + Net Metered)"
    OFF_GRID = "Off-Grid (Battery Only)"
    DAYLIGHT = "Daylight Solar-Direct (Battery-Less Grid-Blending)"



class SolarPanelSpec(BaseModel):
    """Specification of solar photovoltaic module."""

    brand: str = Field(default="Longi Solar", description="Panel manufacturer e.g. Longi, Jinko, JA Solar")
    model: str = Field(default="Hi-MO 6 Explorer LR5-72HTH 585W", description="Module model line")
    wattage_wp: int = Field(default=585, ge=300, le=750, description="Rated peak power per panel in Watts")
    cell_technology: str = Field(default="N-Type TOPCon / HPBC", description="Solar cell semiconductor tech")
    efficiency_percentage: float = Field(default=22.6, description="Module efficiency percentage")
    degradation_year1_pct: float = Field(default=1.5, description="First year degradation percentage")
    annual_degradation_pct: float = Field(default=0.4, description="Linear annual degradation percentage")
    warranty_years_product: int = Field(default=12, description="Product craftsmanship warranty")
    warranty_years_performance: int = Field(default=25, description="Linear power output warranty")


class PunjabSolarProfile(BaseModel):
    """Punjab solar irradiance profile and monthly generation benchmarks.
    
    In Punjab (Faisalabad / Central Punjab), annual average yield is ~125 kWh / kWp / month.
    Seasonal swings account for winter fog (smog in Dec/Jan) and intense summer sunshine (Apr-Jun).
    """

    region: str = Field(default="Punjab (FESCO Region / Faisalabad)", description="Climatic zone")
    base_monthly_yield_per_kw: float = Field(default=125.0, description="Benchmark monthly generation per kW in Punjab (~125 units)")
    
    # Monthly yield weights: average over 12 months = 1.0 (mean = 125 units/kW)
    # Winter smog/fog: Dec (0.72 = ~90u/kW), Jan (0.76 = ~95u/kW)
    # Peak summer: May (1.24 = ~155u/kW), Jun (1.20 = ~150u/kW)
    monthly_yield_factors: Dict[str, float] = Field(
        default={
            "Jan": 0.76,  # ~95 units/kW
            "Feb": 0.88,  # ~110 units/kW
            "Mar": 1.08,  # ~135 units/kW
            "Apr": 1.16,  # ~145 units/kW
            "May": 1.24,  # ~155 units/kW
            "Jun": 1.20,  # ~150 units/kW
            "Jul": 1.12,  # ~140 units/kW
            "Aug": 1.08,  # ~135 units/kW
            "Sep": 1.04,  # ~130 units/kW
            "Oct": 1.00,  # ~125 units/kW
            "Nov": 0.84,  # ~105 units/kW
            "Dec": 0.72,  # ~90 units/kW
        },
        description="Relative seasonal factor multiplier for each month",
    )

    def get_monthly_units_per_kw(self, month: str) -> float:
        """Calculate generation in kWh for 1 kW installed in the given month."""
        factor = self.monthly_yield_factors.get(month[:3].title(), 1.0)
        return round(self.base_monthly_yield_per_kw * factor, 1)


class SystemRecommendation(BaseModel):
    """Comprehensive solar sizing recommendation based on consumer load and Punjab irradiance."""

    system_type: SystemType = Field(default=SystemType.ON_GRID)
    recommended_dc_kw: float = Field(ge=1.0, description="Recommended DC solar array size in kWp")
    inverter_kw: float = Field(ge=1.0, description="Recommended AC inverter capacity in kW")
    inverter_model: str = Field(default="Tier-1 Three Phase String Inverter", description="Inverter type/brand")
    panel_spec: SolarPanelSpec = Field(default_factory=SolarPanelSpec)
    panel_count: int = Field(ge=2, description="Total number of solar panels required")
    
    # Roof space
    rooftop_area_sqft_required: float = Field(description="Approximate shadow-free rooftop area needed in sq. ft")
    
    # Generation metrics
    estimated_monthly_generation_kwh: float = Field(description="Average monthly generation in units (kWh)")
    estimated_annual_generation_kwh: float = Field(description="Estimated annual generation in units (kWh)")
    monthly_generation_curve: Dict[str, float] = Field(default_factory=dict, description="Month-by-month generation in kWh")
    
    # Grid & Sanctioned load compliance (NEPRA / FESCO regulations)
    sanctioned_load_kw: float = Field(description="Consumer's existing sanctioned load from FESCO bill")
    load_expansion_needed: bool = Field(description="True if system size exceeds sanctioned load")
    required_load_extension_kw: float = Field(default=0.0, description="Difference in kW if sanctioned load needs extension")
    net_metering_eligible: bool = Field(default=True, description="Eligible for NEPRA net metering (usually 3-phase >= 5kW)")
    compliance_notes: List[str] = Field(default_factory=list, description="Regulatory compliance and connection recommendations")

    @computed_field
    @property
    def dc_ac_ratio(self) -> float:
        """DC-to-AC oversizing ratio (typically 1.15 to 1.25 for optimal yield in Punjab)."""
        if self.inverter_kw <= 0:
            return 1.0
        return round(self.recommended_dc_kw / self.inverter_kw, 2)
