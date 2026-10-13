"""Unit tests for the solar sizing engine."""

from __future__ import annotations

from fesco_solar.engine.sizing import SolarSizingEngine
from fesco_solar.models.bill import (
    ConsumerDetails,
    ElectricityBill,
    MonthlyRecord,
    TariffInfo,
)
from fesco_solar.models.solar import SystemType


def create_sample_bill(sanctioned_load_kw: float, summer_units: int = 800, winter_units: int = 350) -> ElectricityBill:
    """Helper to generate a mock 12-month bill."""
    consumer = ConsumerDetails(reference_number="13131241234567U")
    tariff = TariffInfo(sanctioned_load_kw=sanctioned_load_kw)

    months = ["OCT", "NOV", "DEC", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP"]
    records = []
    for m in months:
        if m in ["JUN", "JUL", "AUG"]:
            u = summer_units
        elif m in ["DEC", "JAN"]:
            u = winter_units
        else:
            u = int((summer_units + winter_units) / 2)
        records.append(MonthlyRecord(month_name=f"{m}-25", units_consumed=u, bill_amount_pkr=u * 50))

    return ElectricityBill(
        consumer=consumer,
        tariff=tariff,
        current_units=summer_units,
        current_bill_pkr=summer_units * 50,
        history=records,
    )


def test_sizing_within_sanctioned_load():
    """Test sizing when load is compliant."""
    bill = create_sample_bill(sanctioned_load_kw=10.0, summer_units=700, winter_units=300)
    engine = SolarSizingEngine()
    rec = engine.size_system(bill, system_type=SystemType.ON_GRID)

    assert rec.recommended_dc_kw >= 4.0
    assert rec.panel_count % 2 == 0  # Even number of panels
    assert rec.rooftop_area_sqft_required > 0
    # Sanctioned load 10.0 kW should comfortably accommodate a ~5-6kW system
    assert not rec.load_expansion_needed
    assert rec.required_load_extension_kw == 0.0


def test_sizing_exceeding_sanctioned_load():
    """Test that engine flags load expansion when system size exceeds sanctioned load."""
    # Consumer has high consumption (1200 summer units) but only 5.0 kW sanctioned load
    bill = create_sample_bill(sanctioned_load_kw=5.0, summer_units=1200, winter_units=500)
    engine = SolarSizingEngine()
    rec = engine.size_system(bill, system_type=SystemType.ON_GRID)

    assert rec.inverter_kw > 5.0
    assert rec.load_expansion_needed is True
    assert rec.required_load_extension_kw > 0.0
    assert any("[WARNING]" in note for note in rec.compliance_notes)


def test_custom_kw_override():
    """Test manual capacity override."""
    bill = create_sample_bill(sanctioned_load_kw=15.0)
    engine = SolarSizingEngine()
    rec = engine.size_system(bill, custom_kw=10.0)

    # With 585W panels, 18 panels = 10.53 kWp
    assert 9.5 <= rec.recommended_dc_kw <= 11.0
    assert rec.inverter_kw >= 8.0
