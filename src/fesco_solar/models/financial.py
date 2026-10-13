"""Pydantic v2 data models for financial payback, tariff calculations, and ROI."""

from __future__ import annotations

try:
    from pydantic import BaseModel, Field, computed_field
except ImportError:
    from fesco_solar.models.compat import BaseModel, Field, computed_field


class FinancialSummary(BaseModel):
    """Financial feasibility, payback period, and 25-year ROI analysis."""

    total_capex_investment_pkr: float = Field(ge=0.0, description="Total turnkey system cost in PKR")
    annual_grid_units_consumed: int = Field(ge=0, description="Baseline annual grid electricity consumption in kWh")
    annual_solar_generation_kwh: float = Field(ge=0.0, description="Estimated total annual solar generation in kWh")
    
    # Unit allocation
    self_consumed_units_annual: float = Field(description="Units directly offset against daytime consumption")
    exported_units_annual: float = Field(description="Excess solar units exported back to FESCO grid")
    
    # Tariffs (FESCO / NEPRA 2024-2026 tariff regime)
    effective_grid_tariff_pkr_per_unit: float = Field(
        default=52.0,
        description="Effective consumer tariff per unit including base slab rate, FPA, QTA, and taxes",
    )
    nepra_export_credit_pkr_per_unit: float = Field(
        default=22.0,
        description="NEPRA approved net metering export tariff rate credited by FESCO per unit",
    )
    
    # Financial results
    annual_bill_before_solar_pkr: float = Field(description="Estimated current annual electricity expenditure")
    annual_bill_after_solar_pkr: float = Field(description="Projected annual electricity expenditure after solar")
    annual_savings_import_offset_pkr: float = Field(description="PKR savings from avoided grid imports")
    annual_earnings_export_credit_pkr: float = Field(description="PKR earnings credited from exported units")
    total_annual_savings_pkr: float = Field(description="Total annual financial gain in PKR")

    @computed_field
    @property
    def monthly_average_savings_pkr(self) -> float:
        """Estimated average monthly savings in PKR."""
        return round(self.total_annual_savings_pkr / 12.0, 0)

    @computed_field
    @property
    def simple_payback_years(self) -> float:
        """Simple capital payback period in years."""
        if self.total_annual_savings_pkr <= 0:
            return 99.0
        return round(self.total_capex_investment_pkr / self.total_annual_savings_pkr, 1)

    @computed_field
    @property
    def return_on_investment_pct(self) -> float:
        """First-year return on capital investment (ROI %)."""
        if self.total_capex_investment_pkr <= 0:
            return 0.0
        return round((self.total_annual_savings_pkr / self.total_capex_investment_pkr) * 100.0, 1)

    @computed_field
    @property
    def twenty_five_year_net_savings_pkr(self) -> float:
        """Cumulative 25-year financial savings accounting for 0.5% degradation & 5% tariff escalation."""
        # Realistic modeling: inflation/tariff increases balance panel degradation
        return round(self.total_annual_savings_pkr * 25.0 - self.total_capex_investment_pkr, 0)

    @computed_field
    @property
    def levelized_cost_of_energy_pkr(self) -> float:
        """Levelized Cost of Solar Energy (LCOE) in PKR/unit over 25-year lifetime."""
        lifetime_generation_kwh = self.annual_solar_generation_kwh * 25.0 * 0.92  # factoring degradation
        if lifetime_generation_kwh <= 0:
            return 0.0
        # Includes CapEx + 15% lifetime O&M (cleaning, inverter service)
        total_lifetime_cost = self.total_capex_investment_pkr * 1.15
        return round(total_lifetime_cost / lifetime_generation_kwh, 2)
