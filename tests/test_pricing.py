"""Unit tests for pricing and financial payback engines."""

from __future__ import annotations

import os
from fesco_solar.engine.sizing import SolarSizingEngine
from fesco_solar.extractors.pitc_online import PitcOnlineExtractor
from fesco_solar.pricing.payback import FinancialPaybackEngine
from fesco_solar.pricing.service import DynamicPricingService


def test_pricing_service_cache(tmp_path):
    """Test rates cache saving and loading."""
    cache_file = str(tmp_path / "rates_test.json")
    service = DynamicPricingService(cache_path=cache_file)

    # First call will generate/save baseline cache
    cache = service.get_solar_rates(force_refresh=True)
    assert os.path.exists(cache_file)
    assert len(cache.rates) >= 4
    assert cache.average_rate_per_watt > 20.0

    # Second call should read from cached file
    cached_again = service.get_solar_rates(force_refresh=False)
    assert cached_again.rates[0].brand == cache.rates[0].brand


def test_turnkey_bos_calculation(tmp_path):
    """Test turnkey BOS cost components."""
    cache_file = str(tmp_path / "rates_bos.json")
    service = DynamicPricingService(cache_path=cache_file)

    extractor = PitcOnlineExtractor()
    bill = extractor.extract("13131241234567U")
    sizing = SolarSizingEngine()
    rec = sizing.size_system(bill)

    bos = service.calculate_turnkey_bos(rec)
    assert bos.panels_cost_pkr > 0
    assert bos.inverter_cost_pkr > 0
    assert bos.mounting_structure_cost_pkr > 0
    assert bos.electrical_bos_cost_pkr > 0
    assert bos.grounding_earthing_cost_pkr > 0
    assert bos.net_metering_facilitation_pkr > 0
    assert bos.installation_labor_cost_pkr > 0
    assert bos.total_turnkey_cost_pkr > 500000.0


def test_financial_payback_engine(tmp_path):
    """Test financial payback and ROI calculations."""
    cache_file = str(tmp_path / "rates_fin.json")
    service = DynamicPricingService(cache_path=cache_file)

    extractor = PitcOnlineExtractor()
    bill = extractor.extract("13131241234567U")
    sizing = SolarSizingEngine()
    rec = sizing.size_system(bill)
    bos = service.calculate_turnkey_bos(rec)

    payback_engine = FinancialPaybackEngine()
    fin = payback_engine.calculate_payback(bill, rec, bos)

    assert fin.total_annual_savings_pkr > 0
    assert 2.0 <= fin.simple_payback_years <= 6.5
    assert fin.return_on_investment_pct > 15.0
    assert fin.twenty_five_year_net_savings_pkr > bos.total_turnkey_cost_pkr
