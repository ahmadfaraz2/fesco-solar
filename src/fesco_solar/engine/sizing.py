"""Solar sizing engine accounting for seasonal swings, Punjab irradiance, and sanctioned load."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from fesco_solar.models.bill import ElectricityBill
from fesco_solar.models.solar import (
    PunjabSolarProfile,
    SolarPanelSpec,
    SystemRecommendation,
    SystemType,
)


class SolarSizingEngine:
    """Intelligent sizing engine for photovoltaic systems in Punjab / FESCO territory."""

    def __init__(self, profile: Optional[PunjabSolarProfile] = None):
        self.profile = profile or PunjabSolarProfile()

    def size_system(
        self,
        bill: ElectricityBill,
        system_type: SystemType = SystemType.ON_GRID,
        target_offset_pct: float = 100.0,
        panel_spec: Optional[SolarPanelSpec] = None,
        custom_kw: Optional[float] = None,
    ) -> SystemRecommendation:
        """Calculate optimal solar system sizing based on bill analysis and solar irradiance.
        
        Args:
            bill: Parsed ElectricityBill instance.
            system_type: On-Grid or Hybrid system.
            target_offset_pct: Target annual consumption offset percentage (default 100%).
            panel_spec: Solar panel technical specifications (default 585W Tier-1).
            custom_kw: Explicit system capacity override if requested by user.
        """
        panel = panel_spec or SolarPanelSpec()
        sanctioned_load = bill.tariff.sanctioned_load_kw

        # 1. Analyze annual consumption and seasonal swings
        annual_units = bill.total_annual_units
        avg_monthly_units = bill.average_monthly_units
        peak_summer_units = bill.peak_summer_units
        winter_units = bill.winter_minimum_units
        seasonal_swing = bill.seasonal_swing_ratio

        # 2. Determine Required DC Capacity
        # Punjab benchmark: ~125 units (kWh) per kW per month = 1,500 units per kW per year
        annual_yield_per_kw = self.profile.base_monthly_yield_per_kw * 12.0  # 1500 kWh/kW/yr
        
        if custom_kw and custom_kw > 0:
            target_dc_kw = custom_kw
        else:
            # Baseline capacity needed to meet annual target offset
            base_kw_needed = (annual_units * (target_offset_pct / 100.0)) / annual_yield_per_kw
            
            # If seasonal swing is extreme (> 2.0x between summer and winter),
            # provide slight buffer (5-10%) so consumer does not get pushed into high penalty slabs in summer
            if seasonal_swing >= 2.2:
                base_kw_needed *= 1.05
            
            if system_type == SystemType.DAYLIGHT:
                # In daylight setups, can be sized for micro systems down to 2 panels (~1.17 kWp)
                target_dc_kw = max(1.17, base_kw_needed)
            else:
                target_dc_kw = max(3.0, base_kw_needed)

        # 3. Panel Count and Realized DC Capacity
        panel_wattage_kw = panel.wattage_wp / 1000.0
        # Round up panel count to ensure strings can be balanced (even number of panels)
        raw_panel_count = math.ceil(target_dc_kw / panel_wattage_kw)
        panel_count = raw_panel_count if raw_panel_count % 2 == 0 else raw_panel_count + 1
        realized_dc_kw = round(panel_count * panel_wattage_kw, 2)

        # 4. Inverter Sizing (Standard DC/AC oversizing ~1.15 to 1.25)
        if system_type == SystemType.DAYLIGHT:
            standard_inverters = [1.2, 1.5, 2.0, 2.5, 3.0, 3.2, 4.0, 5.0, 6.0]
        else:
            standard_inverters = [3.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 17.0, 20.0, 25.0, 30.0, 40.0, 50.0]

        optimal_ac_kw = realized_dc_kw / 1.20  # target 1.20 DC/AC ratio
        inverter_kw = min((inv for inv in standard_inverters if inv >= optimal_ac_kw), default=standard_inverters[-1])

        # Inverter description
        if system_type == SystemType.HYBRID:
            inv_model = f"{inverter_kw}kW Hybrid Smart Inverter (High-Voltage Battery Ready)"
        elif system_type == SystemType.DAYLIGHT:
            if inverter_kw <= 1.5:
                inv_model = f"{inverter_kw}kW Micro Solar-Direct Inverter (Fronus PV9000 / Inverex - Work-Without-Battery)"
            else:
                inv_model = f"{inverter_kw}kW Single-Phase Solar-Direct Inverter (Work-Without-Battery, Grid-Blending)"
        else:
            inv_model = f"{inverter_kw}kW Three-Phase On-Grid String Inverter (Dual MPPT, IP65)"


        # 5. Sanctioned Load and Regulatory Compliance
        load_expansion_needed = False
        required_load_extension_kw = 0.0
        compliance_notes = []

        if system_type == SystemType.DAYLIGHT:
            net_metering_eligible = False
            compliance_notes.append(
                f"[DAYLIGHT BATTERY-LESS] Solar-Direct Inverter operates behind-the-meter on Single-Phase AC with automatic grid blending. "
                "Generates pure sine wave AC directly from sunlight during the day without requiring any battery bank."
            )
            compliance_notes.append(
                "[NO GREEN METER NEEDED] Does not require 3-Phase meter conversion, FESCO net-metering approvals, or WAPDA green meter fees."
            )
            if inverter_kw > sanctioned_load:
                compliance_notes.append(
                    f"[SAFE RESIDENTIAL OPERATION] Inverter capacity ({inverter_kw} kW) exceeds sanctioned load ({sanctioned_load} kW). "
                    "Inverter limits import from grid and prioritizes free solar generation during daylight hours."
                )
            else:
                compliance_notes.append(
                    f"[COMPLIANT] System capacity ({inverter_kw} kW) is within existing FESCO sanctioned load ({sanctioned_load} kW)."
                )
        else:
            # NEPRA Net Metering Regulations: Installed capacity cannot exceed 100% of sanctioned load.
            if inverter_kw > sanctioned_load:
                load_expansion_needed = True
                required_load_extension_kw = round(inverter_kw - sanctioned_load, 1)
                compliance_notes.append(
                    f"[WARNING] Inverter capacity ({inverter_kw} kW) exceeds consumer's sanctioned load ({sanctioned_load} kW). "
                    f"FESCO regulations require an extension of sanctioned load by at least {required_load_extension_kw} kW before applying for Net Metering."
                )
            else:
                compliance_notes.append(
                    f"[COMPLIANT] System size ({inverter_kw} kW) is within FESCO sanctioned load ({sanctioned_load} kW)."
                )

            # Net metering 3-phase eligibility check
            is_three_phase = "3" in bill.tariff.phase_type or sanctioned_load >= 5.0
            net_metering_eligible = True
            if not is_three_phase:
                compliance_notes.append(
                    "[NOTICE] Net Metering requires a 3-Phase connection. Single-phase meters must be converted to 3-Phase prior to green meter installation."
                )
            if realized_dc_kw < 5.0:
                compliance_notes.append(
                    "[INFO] NEPRA typically recommends net-metered installations to be 5 kW and above for commercial feasibility."
                )


        # 6. Monthly Generation Calculations in Punjab
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthly_generation: Dict[str, float] = {}
        total_annual_generation = 0.0

        for m in months:
            yield_per_kw = self.profile.get_monthly_units_per_kw(m)
            gen_units = round(realized_dc_kw * yield_per_kw, 1)
            monthly_generation[m] = gen_units
            total_annual_generation += gen_units

        total_annual_generation = round(total_annual_generation, 1)
        estimated_monthly_gen = round(total_annual_generation / 12.0, 1)

        # 7. Rooftop Space Estimation (~70 sq ft per kW of installed DC capacity)
        rooftop_sqft = round(realized_dc_kw * 70.0, 0)

        return SystemRecommendation(
            system_type=system_type,
            recommended_dc_kw=realized_dc_kw,
            inverter_kw=inverter_kw,
            inverter_model=inv_model,
            panel_spec=panel,
            panel_count=panel_count,
            rooftop_area_sqft_required=rooftop_sqft,
            estimated_monthly_generation_kwh=estimated_monthly_gen,
            estimated_annual_generation_kwh=total_annual_generation,
            monthly_generation_curve=monthly_generation,
            sanctioned_load_kw=sanctioned_load,
            load_expansion_needed=load_expansion_needed,
            required_load_extension_kw=required_load_extension_kw,
            net_metering_eligible=net_metering_eligible,
            compliance_notes=compliance_notes,
        )
