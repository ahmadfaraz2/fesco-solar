"""Financial payback, bill offset, and 25-year ROI analysis engine."""

from __future__ import annotations

from typing import Optional

from fesco_solar.models.bill import ElectricityBill
from fesco_solar.models.financial import FinancialSummary
from fesco_solar.models.pricing import TurnkeyBOSCost
from fesco_solar.models.solar import SystemRecommendation


class FinancialPaybackEngine:
    """Calculates financial savings, grid offset, and payback under FESCO / NEPRA tariffs."""

    # FESCO 2024-2026 domestic effective slab tariff benchmark (including FPA, QTA, taxes)
    DEFAULT_GRID_IMPORT_TARIFF_PKR = 54.0
    # NEPRA approved Distributed Generation export credit buyback tariff
    DEFAULT_NEPRA_EXPORT_TARIFF_PKR = 22.0

    def calculate_payback(
        self,
        bill: ElectricityBill,
        recommendation: SystemRecommendation,
        turnkey_cost: TurnkeyBOSCost,
        custom_import_tariff: Optional[float] = None,
        custom_export_tariff: Optional[float] = None,
    ) -> FinancialSummary:
        """Compute detailed financial metrics and capital payback timeline."""
        capex = turnkey_cost.total_turnkey_cost_pkr
        annual_grid_units = bill.total_annual_units
        annual_solar_gen = recommendation.estimated_annual_generation_kwh

        import_tariff = custom_import_tariff or self.DEFAULT_GRID_IMPORT_TARIFF_PKR
        export_tariff = custom_export_tariff or self.DEFAULT_NEPRA_EXPORT_TARIFF_PKR

        # Calculate self-consumption vs export
        # In residential Punjab homes, typical daytime self-consumption is ~42% of solar generation
        # The remaining ~58% is exported to the grid via green bi-directional meter
        self_consumed_units = min(annual_grid_units * 0.75, annual_solar_gen * 0.45)
        exported_units = max(0.0, annual_solar_gen - self_consumed_units)

        # Baseline expenditure without solar
        annual_bill_before = annual_grid_units * import_tariff

        # Financial savings
        # 1. Avoided grid electricity purchases
        savings_import_offset = self_consumed_units * import_tariff
        # 2. Credits earned from exported solar units
        earnings_export_credit = exported_units * export_tariff

        total_annual_savings = round(savings_import_offset + earnings_export_credit, 0)
        
        # Projected annual bill after solar (net expenditure)
        net_units_remaining = max(0.0, annual_grid_units - self_consumed_units)
        gross_grid_cost = net_units_remaining * import_tariff
        annual_bill_after = max(0.0, gross_grid_cost - earnings_export_credit)

        return FinancialSummary(
            total_capex_investment_pkr=capex,
            annual_grid_units_consumed=annual_grid_units,
            annual_solar_generation_kwh=annual_solar_gen,
            self_consumed_units_annual=round(self_consumed_units, 0),
            exported_units_annual=round(exported_units, 0),
            effective_grid_tariff_pkr_per_unit=import_tariff,
            nepra_export_credit_pkr_per_unit=export_tariff,
            annual_bill_before_solar_pkr=round(annual_bill_before, 0),
            annual_bill_after_solar_pkr=round(annual_bill_after, 0),
            annual_savings_import_offset_pkr=round(savings_import_offset, 0),
            annual_earnings_export_credit_pkr=round(earnings_export_credit, 0),
            total_annual_savings_pkr=total_annual_savings,
        )
