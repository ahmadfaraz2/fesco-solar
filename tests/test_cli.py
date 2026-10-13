"""End-to-end integration tests for CLI commands."""

from __future__ import annotations

import os
import pytest
from typer.testing import CliRunner
from fesco_solar.cli.main import app

runner = CliRunner()


def test_cli_help():
    """Test top-level CLI help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "FESCO" in result.output
    assert "analyze" in result.output
    assert "rates" in result.output


def test_cli_rates():
    """Test 'rates' subcommand prints pricing table."""
    result = runner.invoke(app, ["rates"])
    assert result.exit_code == 0
    assert "PKR / Watt" in result.output
    assert "Longi" in result.output


def test_cli_quick_quote():
    """Test 'quick-quote' subcommand prints quote."""
    result = runner.invoke(app, ["quick-quote", "--units", "800", "--load", "6.0"])
    assert result.exit_code == 0
    assert "Consumer & Connection Profile" in result.output
    assert "Engineered System Sizing" in result.output
    assert "Financial Feasibility" in result.output


def test_cli_analyze_online_ref():
    """Test 'analyze' with online reference if TEST_FESCO_REF is provided in environment."""
    test_ref = os.environ.get("TEST_FESCO_REF")
    if not test_ref:
        pytest.skip("TEST_FESCO_REF not configured (protects personal data)")
    result = runner.invoke(app, ["analyze", "--ref", test_ref])
    if result.exit_code == 0:
        assert test_ref[:6] in result.output
        assert "Turnkey Balance of System" in result.output
        assert "Simple Payback" in result.output
    else:
        assert "Online Portal Error" in result.output


def test_cli_analyze_fake_ref_fails():
    """Test 'analyze' with non-existent reference fails with exit code 1 (no dummy data fallback)."""
    result = runner.invoke(app, ["analyze", "--ref", "99999999999999"])
    assert result.exit_code == 1
    assert "Online Portal Error" in result.output


def test_cli_demo():
    """Test 'demo' subcommand."""
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "FESCO-SOLAR" in result.output


def test_cli_analyze_pdf():
    """Test 'analyze' with local PDF bill."""
    result = runner.invoke(app, ["analyze", "--pdf", "data/sample_fesco_bill.pdf"])
    assert result.exit_code == 0
    assert "1313124" in result.output
    assert "HAJI ABDUL" in result.output
    assert "7.0 kW" in result.output
    assert "Turnkey Balance of System" in result.output




def test_cli_analyze_pdf_missing_file():
    """Test 'analyze' with non-existent PDF file reports clear error."""
    result = runner.invoke(app, ["analyze", "--pdf", "non_existent.pdf"])
    assert result.exit_code == 1
    assert "Error: File not found" in result.output


def test_cli_bill_command():
    """Test 'bill' command outputs itemized billing details."""
    result = runner.invoke(app, ["bill", "--pdf", "data/sample_fesco_bill.pdf"])
    assert result.exit_code == 0
    assert "Official FESCO Computerized" in result.output
    assert "1313124" in result.output


def test_cli_analyze_daylight():
    """Test 'analyze' with --type daylight battery-less architecture."""
    result = runner.invoke(app, ["analyze", "--pdf", "data/sample_fesco_bill.pdf", "--type", "daylight"])
    assert result.exit_code == 0
    assert "Solar-Direct" in result.output
    assert "Turnkey Balance of System" in result.output


