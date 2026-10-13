"""Unit tests for Pydantic v2 data models in fesco-solar."""

from __future__ import annotations

import pytest
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


def test_consumer_details_clean_reference():
    """Test 14-digit reference number validation and normalization."""
    consumer = ConsumerDetails(
        reference_number=" 13 13124 1234567 U ",
        consumer_name="Tariq Mahmood",
    )
    assert consumer.reference_number == "13131241234567U"
    assert consumer.consumer_name == "Tariq Mahmood"

    # Too short reference number should raise ValueError
    with pytest.raises(ValueError):
        ConsumerDetails(reference_number="12345")


def test_electricity_bill_computed_fields():
    """Test computed metrics on ElectricityBill model."""
    consumer = ConsumerDetails(reference_number="13131241234567U")
    tariff = TariffInfo(sanctioned_load_kw=5.0)

    records = [
        MonthlyRecord(month_name="JAN-25", units_consumed=300, bill_amount_pkr=15000),
        MonthlyRecord(month_name="FEB-25", units_consumed=350, bill_amount_pkr=17500),
        MonthlyRecord(month_name="JUN-25", units_consumed=900, bill_amount_pkr=45000),
        MonthlyRecord(month_name="JUL-25", units_consumed=1000, bill_amount_pkr=50000),
    ]

    bill = ElectricityBill(
        consumer=consumer,
        tariff=tariff,
        current_units=1000,
        current_bill_pkr=50000,
        history=records,
    )

    assert bill.total_annual_units == 2550
    assert bill.average_monthly_units == 637.5
    assert bill.peak_summer_units == 1000
    assert bill.winter_minimum_units == 300
    assert round(bill.seasonal_swing_ratio, 2) == 3.33


def test_punjab_solar_profile():
    """Test Punjab solar irradiance benchmark (~125 units/kW/month)."""
    profile = PunjabSolarProfile()
    assert profile.base_monthly_yield_per_kw == 125.0
    
    # May should be high yield, Dec should be lower due to smog/fog
    assert profile.get_monthly_units_per_kw("May") > profile.get_monthly_units_per_kw("Dec")
    assert profile.get_monthly_units_per_kw("May") >= 150.0
    assert profile.get_monthly_units_per_kw("Dec") <= 95.0


def test_turnkey_bos_cost_breakdown():
    """Test Turnkey BOS cost summation and cost per watt."""
    bos = TurnkeyBOSCost(
        system_capacity_kw=10.0,
        panel_model="Longi 585W TOPCon",
        rate_per_watt_pkr=30.0,
        panels_cost_pkr=300000,
        inverter_model="10kW String Inverter",
        inverter_cost_pkr=270000,
        structure_type="GI L2/L3",
        mounting_structure_cost_pkr=140000,
        electrical_bos_cost_pkr=210000,
        grounding_earthing_cost_pkr=75000,
        net_metering_facilitation_pkr=115000,
        installation_labor_cost_pkr=95000,
    )

    expected_total = 300000 + 270000 + 140000 + 210000 + 75000 + 115000 + 95000
    assert bos.total_turnkey_cost_pkr == expected_total
    assert bos.cost_per_watt_pkr == round(expected_total / 10000.0, 2)
