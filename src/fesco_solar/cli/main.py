"""Polished Typer CLI interface for FESCO Solar Advisor using Rich."""

from __future__ import annotations

import os
from typing import Optional
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fesco_solar.engine.sizing import SolarSizingEngine
from fesco_solar.extractors.pdf_parser import PdfBillExtractor
from fesco_solar.extractors.pitc_online import PitcOnlineExtractor
from fesco_solar.models.bill import ElectricityBill
from fesco_solar.models.solar import SystemType
from fesco_solar.pricing.payback import FinancialPaybackEngine
from fesco_solar.pricing.service import DynamicPricingService

app = typer.Typer(
    name="fesco-solar",
    help="⚡ Intelligent Solar Sizing, Bill Extraction & Payback Advisor for FESCO Consumers in Punjab.",
    add_completion=False,
)

console = Console()


def print_banner() -> None:
    """Print branded CLI banner."""
    banner_text = Text()
    banner_text.append("☀️  FESCO-SOLAR ", style="bold yellow")
    banner_text.append("| Punjab Rooftop Photovoltaic & Net-Metering Advisor\n", style="bold cyan")
    banner_text.append("   Optimized for Punjab Irradiance (~125 kWh/kW/mo) & NEPRA Distributed Gen Rules", style="dim white")
    console.print(Panel(banner_text, box=box.ROUNDED, border_style="yellow"))


def display_consumer_and_history(bill: ElectricityBill, is_live_verified: bool = False) -> None:
    """Display consumer details and monthly consumption breakdown table with visual bars."""
    # Consumer Summary Box
    info_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    info_table.add_column("Key", style="bold cyan")
    info_table.add_column("Value", style="white")
    info_table.add_column("Key2", style="bold cyan")
    info_table.add_column("Value2", style="white")

    info_table.add_row(
        "Consumer Name:", bill.consumer.consumer_name,
        "Reference Number:", f"[bold green]{bill.consumer.reference_number}[/bold green]"
    )
    info_table.add_row(
        "Address:", bill.consumer.address,
        "Sanctioned Load:", f"[bold magenta]{bill.tariff.sanctioned_load_kw} kW[/bold magenta] ({bill.tariff.phase_type})"
    )
    info_table.add_row(
        "Tariff Category:", bill.tariff.tariff_code,
        "Feeder / Sub-Div:", f"{bill.tariff.feeder_name or 'Local Feeder'} / {bill.consumer.sub_division or 'N/A'}"
    )

    if is_live_verified:
        info_table.add_row(
            "Status:", "[bold green]🟢 ORIGINAL PITC LIVE BILL VERIFIED[/bold green]",
            "Billing Month:", f"[bold cyan]{bill.bill_month}[/bold cyan]"
        )
    elif bill.bill_month:
        info_table.add_row(
            "Billing Month:", f"[bold cyan]{bill.bill_month}[/bold cyan]",
            "Status:", "[yellow]Representative / Offline Cached[/yellow]"
        )

    title_badge = "👤 Consumer & Connection Profile [bold green](Original Bill Verified)[/bold green]" if is_live_verified else "👤 Consumer & Connection Profile"
    console.print(Panel(info_table, title=f"[bold green]{title_badge}[/bold green]", box=box.ROUNDED, border_style="green"))

    # 12-Month Consumption Breakdown
    table = Table(
        title=f"📊 12-Month Billing History & Seasonal Swings (Total: {bill.total_annual_units:,} kWh)",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_footer=True,
    )
    table.add_column("Month", style="bold white", footer="[bold]Annual / Avg[/bold]")
    table.add_column("Units (kWh)", justify="right", style="yellow", footer=f"[bold yellow]{bill.total_annual_units:,} kWh[/bold yellow]")
    table.add_column("Bill (PKR)", justify="right", style="green", footer=f"[bold green]Rs {sum(r.bill_amount_pkr for r in bill.history):,.0f}[/bold green]")
    table.add_column("Seasonal Swing Indicator", justify="left")
    table.add_column("Status", justify="center", style="dim")

    max_u = max(r.units_consumed for r in bill.history) if bill.history else 1
    
    for rec in bill.history:
        # Visual bar representation
        bar_len = int((rec.units_consumed / max_u) * 20)
        is_peak = rec.units_consumed == bill.peak_summer_units
        is_min = rec.units_consumed == bill.winter_minimum_units
        
        if is_peak:
            bar_color = "red"
            note = " [bold red]PEAK SUMMER[/bold red]"
        elif is_min:
            bar_color = "blue"
            note = " [bold blue]WINTER LOW[/bold blue]"
        elif rec.units_consumed > bill.average_monthly_units:
            bar_color = "yellow"
            note = ""
        else:
            bar_color = "cyan"
            note = ""
            
        bar_str = f"[{bar_color}]{'█' * bar_len}[/{bar_color}]{note}"
        
        table.add_row(
            rec.month_name,
            f"{rec.units_consumed:,}",
            f"Rs {rec.bill_amount_pkr:,.0f}",
            bar_str,
            rec.payment_status or "PAID",
        )

    console.print(table)

    # Seasonal Swing Summary Box
    swing_text = Text()
    swing_text.append(f"• Average Monthly Demand: ", style="bold white")
    swing_text.append(f"{bill.average_monthly_units:,.1f} kWh/month\n", style="bold yellow")
    swing_text.append(f"• High Summer Peak: ", style="bold white")
    swing_text.append(f"{bill.peak_summer_units:,} kWh ", style="bold red")
    swing_text.append(f"vs Winter Low: ", style="bold white")
    swing_text.append(f"{bill.winter_minimum_units:,} kWh ", style="bold blue")
    swing_text.append(f"(Seasonal Swing Ratio: ", style="bold white")
    swing_text.append(f"{bill.seasonal_swing_ratio}x)\n", style="bold magenta")
    swing_text.append(
        "• Climate Factor: Punjab experiences high cooling loads (ACs) during May-Aug and winter fog in Dec-Jan. "
        "Sizing is calculated to prevent high summer tariff slab bracket creep.",
        style="dim white",
    )
    console.print(Panel(swing_text, title="[bold yellow]🌡️ Seasonal Variance Analysis[/bold yellow]", box=box.ROUNDED, border_style="yellow"))


def display_recommendation_and_bos(recommendation, turnkey_cost) -> None:
    """Print system sizing recommendation and Turnkey BOS cost table."""
    # Sizing Specs
    rec_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    rec_table.add_column("Parameter", style="bold cyan")
    rec_table.add_column("Value", style="bold white")
    rec_table.add_column("Parameter2", style="bold cyan")
    rec_table.add_column("Value2", style="bold white")

    rec_table.add_row(
        "Recommended DC Capacity:", f"[bold green]{recommendation.recommended_dc_kw:.2f} kWp[/bold green]",
        "Inverter Sizing:", f"[bold green]{recommendation.inverter_kw:.1f} kW[/bold green] (DC/AC {recommendation.dc_ac_ratio}x)"
    )
    rec_table.add_row(
        "PV Modules Count:", f"{recommendation.panel_count} Panels ({recommendation.panel_spec.wattage_wp}W)",
        "Module Tech:", f"{recommendation.panel_spec.cell_technology}"
    )
    rec_table.add_row(
        "Inverter Spec:", recommendation.inverter_model,
        "System Architecture:", f"[cyan]{recommendation.system_type.value}[/cyan]"
    )
    rec_table.add_row(
        "Est. Annual Generation:", f"[bold yellow]{recommendation.estimated_annual_generation_kwh:,.0f} kWh/year[/bold yellow]",
        "Est. Monthly Generation:", f"[yellow]{recommendation.estimated_monthly_generation_kwh:,.0f} kWh/month[/yellow]"
    )
    rec_table.add_row(
        "Roof Shadow-Free Area:", f"{recommendation.rooftop_area_sqft_required:,.0f} sq. ft (~{recommendation.rooftop_area_sqft_required/225:.1f} Marla)",
        "Punjab Specific Yield:", "125 kWh / kWp / Month Benchmark"
    )

    console.print(Panel(rec_table, title="[bold cyan]⚙️ Engineered System Sizing Recommendation[/bold cyan]", box=box.ROUNDED, border_style="cyan"))

    # Sanctioned Load Check Panel
    comp_text = Text()
    for note in recommendation.compliance_notes:
        if "[COMPLIANT]" in note:
            comp_text.append(f"{note}\n", style="bold green")
        elif "[WARNING]" in note:
            comp_text.append(f"{note}\n", style="bold red")
        else:
            comp_text.append(f"{note}\n", style="bold yellow")

    if recommendation.load_expansion_needed:
        comp_text.append(
            f"\n⚠️ ACTION REQUIRED: Inverter ({recommendation.inverter_kw} kW) > Sanctioned Load ({recommendation.sanctioned_load_kw} kW).\n"
            f"Under NEPRA Distributed Generation Regulations, FESCO Net Metering approval requires applying for a "
            f"+{recommendation.required_load_extension_kw:.1f} kW Load Extension prior to green meter installation.",
            style="bold yellow",
        )
        box_style = "red"
        box_title = "[bold red]⚠️ FESCO Sanctioned Load Check: Extension Required[/bold red]"
    else:
        comp_text.append(
            f"\n✅ Ready for Net Metering: Inverter capacity ({recommendation.inverter_kw} kW) is compliant with FESCO sanctioned load ({recommendation.sanctioned_load_kw} kW).",
            style="bold green",
        )
        box_style = "green"
        box_title = "[bold green]✅ FESCO Sanctioned Load Check: 100% Compliant[/bold green]"

    console.print(Panel(comp_text, title=box_title, box=box.ROUNDED, border_style=box_style))

    # Turnkey BOS Table
    bos_table = Table(
        title=f"💰 Turnkey Balance of System (BOS) CapEx Breakdown ({turnkey_cost.cost_per_watt_pkr:.2f} PKR/Watt)",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_footer=True,
    )
    bos_table.add_column("Component", style="bold white", footer="[bold]TOTAL TURNKEY PROJECT COST[/bold]")
    bos_table.add_column("Technical Specification / Scope", style="dim white")
    bos_table.add_column("Cost (PKR)", justify="right", style="bold green", footer=f"[bold green]Rs {turnkey_cost.total_turnkey_cost_pkr:,.0f}[/bold green]")
    bos_table.add_column("Share (%)", justify="right", style="cyan")

    total = turnkey_cost.total_turnkey_cost_pkr
    items = [
        ("Tier-1 Solar PV Modules", f"{turnkey_cost.panel_model} @ Rs {turnkey_cost.rate_per_watt_pkr}/W", turnkey_cost.panels_cost_pkr),
        ("Inverter", turnkey_cost.inverter_model, turnkey_cost.inverter_cost_pkr),
        ("Mounting Structures", turnkey_cost.structure_type, turnkey_cost.mounting_structure_cost_pkr),
        ("Electrical BOS", "DC 4/6mm² copper cables, Schneider MCCB/MCB, Type-II SPD, DB boxes", turnkey_cost.electrical_bos_cost_pkr),
        ("Earthing & Lightning Bore", "Dual chemical grounding bore (< 5 ohms) with copper rods", turnkey_cost.grounding_earthing_cost_pkr),
        ("FESCO Net Metering & Meter", "Green bi-directional 3-phase meter, WAPDA lab test, NEPRA license", turnkey_cost.net_metering_facilitation_pkr),
        ("Turnkey Labor & Commissioning", "Civil work, structural assembly, wiring, testing & commissioning", turnkey_cost.installation_labor_cost_pkr),
    ]

    for name, spec, cost in items:
        pct = (cost / total) * 100.0 if total > 0 else 0
        bos_table.add_row(name, spec, f"Rs {cost:,.0f}", f"{pct:.1f}%")

    console.print(bos_table)


def display_financial_summary(financial) -> None:
    """Print financial payback, savings, and 25-year ROI panel."""
    fin_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    fin_table.add_column("Metric", style="bold cyan")
    fin_table.add_column("Value", style="bold white")
    fin_table.add_column("Metric2", style="bold cyan")
    fin_table.add_column("Value2", style="bold white")

    fin_table.add_row(
        "Total Initial Investment:", f"[bold magenta]Rs {financial.total_capex_investment_pkr:,.0f}[/bold magenta]",
        "Simple Payback Period:", f"[bold green]{financial.simple_payback_years} Years[/bold green]"
    )
    fin_table.add_row(
        "Estimated Annual Savings:", f"[bold green]Rs {financial.total_annual_savings_pkr:,.0f} / year[/bold green]",
        "Annual Return on Investment (ROI):", f"[bold yellow]{financial.return_on_investment_pct}% / year[/bold yellow]"
    )
    fin_table.add_row(
        "Estimated Monthly Savings:", f"[green]Rs {financial.monthly_average_savings_pkr:,.0f} / month[/green]",
        "Levelized Energy Cost (LCOE):", f"[cyan]Rs {financial.levelized_cost_of_energy_pkr:.2f} / unit[/cyan]"
    )
    fin_table.add_row(
        "Self-Consumed Solar Energy:", f"{financial.self_consumed_units_annual:,.0f} kWh (Offset @ Rs {financial.effective_grid_tariff_pkr_per_unit}/u)",
        "Exported Solar Units (FESCO Credit):", f"{financial.exported_units_annual:,.0f} kWh (Credit @ Rs {financial.nepra_export_credit_pkr_per_unit}/u)"
    )
    fin_table.add_row(
        "Current Annual Bill (Without Solar):", f"Rs {financial.annual_bill_before_solar_pkr:,.0f}",
        "Projected Annual Bill (With Solar):", f"[bold green]Rs {financial.annual_bill_after_solar_pkr:,.0f}[/bold green]"
    )
    fin_table.add_row(
        "25-Year Cumulative Net Savings:", f"[bold green]Rs {financial.twenty_five_year_net_savings_pkr:,.0f}[/bold green]",
        "Assumed Grid Tariff / Export Rate:", f"Rs {financial.effective_grid_tariff_pkr_per_unit} / Rs {financial.nepra_export_credit_pkr_per_unit}"
    )

    console.print(Panel(fin_table, title="[bold green]📈 Financial Feasibility & Payback Horizon[/bold green]", box=box.ROUNDED, border_style="green"))


@app.command()
def analyze(
    ref: Optional[str] = typer.Option(
        None,
        "--ref",
        "-r",
        help="14-digit FESCO reference number (fetches online via PITC portal)",
    ),
    pdf: Optional[str] = typer.Option(
        None,
        "--pdf",
        "-p",
        help="Path to local FESCO bill PDF file",
    ),
    system_type_str: str = typer.Option(
        "on-grid",
        "--type",
        "-t",
        help="System architecture: 'on-grid' (net metered) or 'hybrid' (battery backup)",
    ),
    offset: float = typer.Option(
        100.0,
        "--offset",
        "-o",
        help="Target annual consumption offset percentage (default: 100%)",
    ),
    custom_kw: Optional[float] = typer.Option(
        None,
        "--kw",
        help="Explicit system size override in kW",
    ),
    brand: Optional[str] = typer.Option(
        None,
        "--brand",
        "-b",
        help="Preferred solar panel brand (e.g. Longi, Jinko, JA Solar, Canadian)",
    ),
    refresh_rates: bool = typer.Option(
        False,
        "--refresh-rates",
        help="Force fresh scrape of live per-watt solar plate rates in PKR",
    ),
) -> None:
    """Analyze a FESCO electricity bill (via online 14-digit reference number or local PDF)."""
    print_banner()

    if not ref and not pdf:
        console.print(
            "[bold yellow]⚠️ No bill source specified![/bold yellow]\n"
            "Please provide either:\n"
            "  • [green]--ref <14-digit reference>[/green] to fetch from PITC portal, OR\n"
            "  • [green]--pdf <path-to-bill.pdf>[/green] to extract from a local PDF.\n\n"
            "[dim]Tip: Try [bold cyan]fesco-solar demo[/bold cyan] to see a full live demonstration![/dim]"
        )
        raise typer.Exit(code=1)

    # 1. Extract Bill
    with console.status("[bold cyan]Extracting bill data...", spinner="dots"):
        if pdf:
            console.print(f"[dim]Reading local PDF bill: [bold]{pdf}[/bold][/dim]")
            extractor = PdfBillExtractor()
            bill = extractor.extract(pdf)
        else:
            console.print(f"[dim]Querying online PITC billing portal for reference: [bold]{ref}[/bold][/dim]")
            extractor = PitcOnlineExtractor()
            bill = extractor.extract(ref)  # type: ignore

    # 2. Size Solar System
    sizing_engine = SolarSizingEngine()
    sys_type = SystemType.HYBRID if "hybrid" in system_type_str.lower() else SystemType.ON_GRID
    recommendation = sizing_engine.size_system(
        bill=bill,
        system_type=sys_type,
        target_offset_pct=offset,
        custom_kw=custom_kw,
    )

    # 3. Dynamic Pricing & BOS
    pricing_service = DynamicPricingService()
    if refresh_rates:
        console.print("[dim]Fetching live solar rates in PKR...[/dim]")
    pricing_service.get_solar_rates(force_refresh=refresh_rates)
    turnkey_cost = pricing_service.calculate_turnkey_bos(recommendation, selected_brand=brand)

    # 4. Financial Payback
    payback_engine = FinancialPaybackEngine()
    financial = payback_engine.calculate_payback(bill, recommendation, turnkey_cost)

    # 5. Display Rich Results
    is_live = getattr(extractor, "last_fetch_was_live", False)
    display_consumer_and_history(bill, is_live_verified=is_live)
    display_recommendation_and_bos(recommendation, turnkey_cost)
    display_financial_summary(financial)


@app.command()
def rates(
    refresh: bool = typer.Option(
        False,
        "--refresh",
        "-r",
        help="Force fresh scrape of live solar plate market rates in PKR",
    ),
) -> None:
    """Display live per-watt solar plate rates in PKR cached in data/rates_cache.json."""
    print_banner()

    pricing_service = DynamicPricingService()
    with console.status("[bold cyan]Checking live solar plate rates in Pakistan...", spinner="dots"):
        cache = pricing_service.get_solar_rates(force_refresh=refresh)

    source_status = "[bold green]LIVE SCRAPED[/bold green]" if cache.is_live_scraped else "[bold yellow]BENCHMARK INDEX[/bold yellow]"
    console.print(f"\n[dim]Rates Updated: [white]{cache.updated_at}[/white] | Source Status: {source_status}[/dim]\n")

    table = Table(
        title="☀️ Live Solar Plate Market Rates in Pakistan (PKR / Watt)",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_footer=True,
    )
    table.add_column("Brand", style="bold white", footer="[bold]Market Average[/bold]")
    table.add_column("Model Series", style="white")
    table.add_column("Technology", style="dim white")
    table.add_column("Wattage", justify="right", style="cyan")
    table.add_column("Rate (PKR/Watt)", justify="right", style="bold green", footer=f"[bold green]Rs {cache.average_rate_per_watt:.2f}/W[/bold green]")
    table.add_column("Price / Panel (PKR)", justify="right", style="yellow")
    table.add_column("Tier", justify="center", style="magenta")

    for r in cache.rates:
        table.add_row(
            r.brand,
            r.model,
            r.panel_type,
            f"{r.wattage}W",
            f"Rs {r.rate_per_watt_pkr:.2f}",
            f"Rs {r.price_per_panel_pkr:,.0f}",
            r.tier,
        )

    console.print(table)
    console.print(f"[dim]Cache Location: [bold]{pricing_service.cache_path}[/bold][/dim]\n")


@app.command(name="quick-quote")
def quick_quote(
    units: int = typer.Option(
        750,
        "--units",
        "-u",
        help="Average monthly electricity consumption in kWh",
    ),
    load: float = typer.Option(
        5.0,
        "--load",
        "-l",
        help="Sanctioned load on electricity connection in kW",
    ),
    system_type_str: str = typer.Option(
        "on-grid",
        "--type",
        "-t",
        help="System architecture: 'on-grid' or 'hybrid'",
    ),
) -> None:
    """Generate instant solar sizing and turnkey quote based on monthly units."""
    # Build representative bill
    extractor = PitcOnlineExtractor()
    bill = extractor._generate_representative_bill("13131241234567U", "13131241234567")
    bill.tariff.sanctioned_load_kw = load
    # Adjust monthly units to match user input
    factor = units / bill.average_monthly_units if bill.average_monthly_units > 0 else 1.0
    for rec in bill.history:
        rec.units_consumed = int(rec.units_consumed * factor)
        rec.bill_amount_pkr = round(rec.units_consumed * 52.0, 2)

    print_banner()
    sys_type = SystemType.HYBRID if "hybrid" in system_type_str.lower() else SystemType.ON_GRID
    sizing_engine = SolarSizingEngine()
    recommendation = sizing_engine.size_system(bill=bill, system_type=sys_type)

    pricing_service = DynamicPricingService()
    turnkey_cost = pricing_service.calculate_turnkey_bos(recommendation)

    payback_engine = FinancialPaybackEngine()
    financial = payback_engine.calculate_payback(bill, recommendation, turnkey_cost)

    display_consumer_and_history(bill)
    display_recommendation_and_bos(recommendation, turnkey_cost)
    display_financial_summary(financial)


@app.command()
def demo() -> None:
    """Run an end-to-end demonstration with a realistic FESCO 14-digit reference bill."""
    analyze(
        ref="13131241234567U",
        pdf=None,
        system_type_str="on-grid",
        offset=100.0,
        custom_kw=None,
        brand="Longi",
        refresh_rates=False,
    )


def main() -> None:
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
