"""Pydantic v2 data models for live solar pricing, caching, and Turnkey BOS calculations."""

from __future__ import annotations

from typing import List, Optional
try:
    from pydantic import BaseModel, Field, computed_field
except ImportError:
    from fesco_solar.models.compat import BaseModel, Field, computed_field


class SolarPlateRate(BaseModel):
    """Live per-watt market rate for a solar PV brand/model in Pakistan."""

    brand: str = Field(description="Brand name e.g. Longi, Jinko, JA Solar, Canadian Solar")
    model: str = Field(description="Panel series e.g. Hi-MO 6, Tiger Neo N-Type, DeepBlue 4.0")
    panel_type: str = Field(default="Mono PERC / TOPCon Bifacial", description="Cell technology")
    wattage: int = Field(default=585, description="Individual panel nominal power in Watts")
    rate_per_watt_pkr: float = Field(ge=10.0, le=200.0, description="Price in PKR per Watt peak")
    tier: str = Field(default="Tier-1 Bloomberg NEF", description="Manufacturer tier ranking")
    source: str = Field(default="Live Pakistan Solar Index", description="Data source or marketplace")
    last_updated: str = Field(description="ISO or formatted date of price entry")

    @computed_field
    @property
    def price_per_panel_pkr(self) -> float:
        """Total price for single panel module."""
        return round(self.rate_per_watt_pkr * self.wattage, 0)


class RatesCache(BaseModel):
    """Persistent JSON cache for dynamic solar rates."""

    updated_at: str = Field(description="Timestamp when cache was written")
    ttl_seconds: int = Field(default=86400, description="Cache time to live in seconds (default 24h)")
    is_live_scraped: bool = Field(default=True, description="True if retrieved from live web feed")
    source_url: Optional[str] = Field(default=None, description="Scraping source URL or identifier")
    rates: List[SolarPlateRate] = Field(default_factory=list, description="List of panel rates in PKR/Watt")

    @computed_field
    @property
    def average_rate_per_watt(self) -> float:
        """Market average PKR per watt across available Tier-1 brands."""
        if not self.rates:
            return 31.5  # Typical baseline in PKR/watt
        return round(sum(r.rate_per_watt_pkr for r in self.rates) / len(self.rates), 2)


class TurnkeyBOSCost(BaseModel):
    """Complete Turnkey Balance of System (BOS) and installation cost breakdown."""

    system_capacity_kw: float = Field(ge=1.0, description="System DC capacity in kW")
    panel_model: str = Field(description="Selected solar panel model")
    rate_per_watt_pkr: float = Field(description="Applied per-watt plate rate in PKR")
    
    # 1. Solar PV Modules Cost
    panels_cost_pkr: float = Field(description="Total cost of solar panels in PKR")
    
    # 2. Inverter Cost (On-grid / Hybrid string inverter)
    inverter_model: str = Field(description="Inverter specification")
    inverter_cost_pkr: float = Field(description="Inverter unit cost in PKR")
    
    # 3. Mounting Structure (Galvanized Iron L2/L3 frames)
    structure_type: str = Field(default="GI L2/L3 Custom Heavy Duty (140 km/h wind rated)", description="Mounting frame type")
    mounting_structure_cost_pkr: float = Field(description="Mounting structure framing cost in PKR")
    
    # 4. Electrical BOS (DC cables 4/6mm², AC cables, MCCB, SPD, AC/DC DB boxes, changeover)
    electrical_bos_cost_pkr: float = Field(description="DC/AC cables, Schneider/ABB breakers, SPDs, distribution box")
    
    # 5. Earthing & Lightning Protection (Chemical bore grounding < 5 ohms)
    grounding_earthing_cost_pkr: float = Field(description="Dual grounding chemical bore (inverter + lightning arrester)")
    
    # 6. FESCO Net Metering Facilitation & Green Meter
    net_metering_facilitation_pkr: float = Field(description="FESCO Green meter procurement, testing fee & NEPRA licensing")
    
    # 7. Turnkey Installation, Civil Work & Commissioning
    installation_labor_cost_pkr: float = Field(description="Civil foundations, mounting, wiring labor, commissioning")

    @computed_field
    @property
    def total_turnkey_cost_pkr(self) -> float:
        """Total all-inclusive turnkey project cost in PKR."""
        return round(
            self.panels_cost_pkr
            + self.inverter_cost_pkr
            + self.mounting_structure_cost_pkr
            + self.electrical_bos_cost_pkr
            + self.grounding_earthing_cost_pkr
            + self.net_metering_facilitation_pkr
            + self.installation_labor_cost_pkr,
            0,
        )

    @computed_field
    @property
    def cost_per_watt_pkr(self) -> float:
        """Total Turnkey installed cost in PKR per Watt."""
        total_watts = self.system_capacity_kw * 1000.0
        if total_watts <= 0:
            return 0.0
        return round(self.total_turnkey_cost_pkr / total_watts, 2)
