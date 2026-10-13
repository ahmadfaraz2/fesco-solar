"""End-to-end integration tests for CLI commands."""

from __future__ import annotations

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
    """Test 'analyze' with 14-digit reference number."""
    result = runner.invoke(app, ["analyze", "--ref", "13131241234567U"])
    assert result.exit_code == 0
    assert "13131241234567U" in result.output
    assert "Turnkey Balance of System" in result.output
    assert "Simple Payback" in result.output


def test_cli_demo():
    """Test 'demo' subcommand."""
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "FESCO-SOLAR" in result.output
