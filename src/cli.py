"""
Command-line interface for the training planner.

Provides interactive commands for:
- User profile validation
- Methodology viewing
- Reasoning trace generation
"""

import json
from pathlib import Path
from datetime import date, datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from src.schemas import (
    UserProfile,
    CurrentState,
    Goals,
    StressLevel,
    PrimaryGoal,
    RaceDistance,
    HRVTrend,
    MenstrualPhase,
)
from src.validator import MethodologyValidator
from src.trace import save_trace_from_result

# Initialize Typer app and Rich console
app = typer.Typer(
    help="Human-in-the-Loop Training Planner - Transparent, interpretable training guidance"
)
console = Console()


@app.command()
def validate(
    profile: Optional[Path] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Path to existing user profile JSON file",
        exists=True,
    ),
    methodology: Path = typer.Option(
        Path("models/methodology_polarized.json"),
        "--methodology",
        "-m",
        help="Path to methodology JSON file",
        exists=True,
    ),
    save_trace: bool = typer.Option(
        True,
        "--save-trace/--no-trace",
        help="Save reasoning trace to file",
    ),
    trace_format: str = typer.Option(
        "json",
        "--trace-format",
        "-f",
        help="Trace output format (json or markdown)",
    ),
):
    """
    Validate user profile against methodology requirements.

    If no profile is provided, starts interactive profile creation.
    """
    console.print("\n[bold cyan]🏊 🚴 🏃 Human-in-the-Loop Training Planner[/bold cyan]\n")

    # Load methodology
    try:
        validator = MethodologyValidator.from_file(methodology)
        console.print(f"✓ Loaded methodology: [green]{validator.methodology.name}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to load methodology: {e}[/red]")
        raise typer.Exit(1)

    # Get user profile
    if profile:
        # Load from file
        try:
            with open(profile, "r") as f:
                profile_data = json.load(f)
            user_profile = UserProfile(**profile_data)
            console.print(f"✓ Loaded profile: [green]{user_profile.athlete_id}[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Failed to load profile: {e}[/red]")
            raise typer.Exit(1)
    else:
        # Interactive creation
        console.print("[yellow]No profile provided. Starting interactive profile creation...[/yellow]\n")
        user_profile = create_profile_interactive()

    # Display methodology info
    _display_methodology_card(validator.methodology)

    # Run validation
    console.print("\n[bold]Running validation...[/bold]\n")
    result = validator.validate(user_profile)

    # Display results
    _display_validation_result(validator, result)

    # Save trace if requested
    if save_trace:
        trace_dir = Path("reasoning_logs")
        trace_path = save_trace_from_result(result, trace_dir, format=trace_format)
        console.print(f"\n✓ Reasoning trace saved: [cyan]{trace_path}[/cyan]")


@app.command()
def methodology(
    show: str = typer.Option(
        None,
        "--show",
        "-s",
        help="Methodology ID to display",
    ),
    list_all: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List all available methodologies",
    ),
):
    """
    View methodology details and model cards.
    """
    models_dir = Path("models")

    if list_all:
        console.print("\n[bold]Available Methodologies:[/bold]\n")
        for model_file in models_dir.glob("methodology_*.json"):
            with open(model_file) as f:
                data = json.load(f)
            console.print(f"  • [cyan]{data['id']}[/cyan] - {data['name']} (v{data['version']})")
        console.print()
        return

    if show:
        # Find methodology file
        methodology_file = models_dir / f"methodology_{show}.json"
        if not methodology_file.exists():
            # Try exact filename
            methodology_file = models_dir / f"{show}.json"

        if not methodology_file.exists():
            console.print(f"[red]✗ Methodology not found: {show}[/red]")
            console.print(f"[yellow]Available files in {models_dir}:[/yellow]")
            for f in models_dir.glob("*.json"):
                console.print(f"  • {f.name}")
            raise typer.Exit(1)

        try:
            validator = MethodologyValidator.from_file(methodology_file)
            _display_methodology_card(validator.methodology, detailed=True)
        except Exception as e:
            console.print(f"[red]✗ Failed to load methodology: {e}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]Use --show <id> to view a methodology or --list to see all[/yellow]")


def create_profile_interactive() -> UserProfile:
    """
    Interactive user profile creation.

    Returns:
        UserProfile created from user input
    """
    console.print("[bold]Creating User Profile[/bold]")
    console.print("Please answer the following questions about your current state:\n")

    # Basic info
    athlete_id = Prompt.ask("Athlete ID", default=f"athlete_{datetime.now().strftime('%Y%m%d')}")

    # Current state
    console.print("\n[bold cyan]Current State[/bold cyan]")

    sleep_hours = float(
        Prompt.ask("Average sleep hours per night (last 7 days)", default="7.5")
    )

    injury_status = Confirm.ask("Do you have any active injuries or pain?")
    injury_details = None
    if injury_status:
        injury_details = Prompt.ask("Please describe the injury")

    stress_level_str = Prompt.ask(
        "Stress level (last 7 days)",
        choices=["low", "moderate", "high"],
        default="low",
    )
    stress_level = StressLevel(stress_level_str)

    weekly_volume_hours = float(
        Prompt.ask("Average weekly training volume (hours)", default="10.0")
    )

    volume_consistency_weeks = int(
        Prompt.ask("How many consecutive weeks at this volume?", default="4")
    )

    recent_illness = Confirm.ask("Any illness in the last 14 days?")

    # Goals
    console.print("\n[bold cyan]Goals[/bold cyan]")

    primary_goal_str = Prompt.ask(
        "Primary goal",
        choices=["race_performance", "base_building", "general_fitness"],
        default="race_performance",
    )
    primary_goal = PrimaryGoal(primary_goal_str)

    race_date = None
    race_distance = None
    weeks_to_race = None

    if primary_goal == PrimaryGoal.RACE_PERFORMANCE:
        race_date_str = Prompt.ask("Race date (YYYY-MM-DD)", default="2026-06-01")
        race_date = date.fromisoformat(race_date_str)

        race_distance_str = Prompt.ask(
            "Race distance",
            choices=["sprint", "olympic", "half_ironman", "ironman"],
            default="olympic",
        )
        race_distance = RaceDistance(race_distance_str)

        # Calculate weeks to race
        weeks_to_race = max(1, int((race_date - date.today()).days / 7))

    # Build profile
    current_state = CurrentState(
        sleep_hours=sleep_hours,
        injury_status=injury_status,
        injury_details=injury_details,
        stress_level=stress_level,
        weekly_volume_hours=weekly_volume_hours,
        volume_consistency_weeks=volume_consistency_weeks,
        recent_illness=recent_illness,
    )

    goals = Goals(
        primary_goal=primary_goal,
        race_date=race_date,
        race_distance=race_distance,
        weeks_to_race=weeks_to_race,
    )

    profile = UserProfile(
        athlete_id=athlete_id,
        profile_date=date.today(),
        current_state=current_state,
        goals=goals,
    )

    # Offer to save
    if Confirm.ask("\nSave this profile for future use?"):
        profile_dir = Path("user_profiles")
        profile_dir.mkdir(exist_ok=True)
        profile_path = profile_dir / f"{athlete_id}.json"

        with open(profile_path, "w") as f:
            json.dump(profile.model_dump(mode="json"), f, indent=2, default=str)

        console.print(f"✓ Profile saved: [cyan]{profile_path}[/cyan]\n")

    return profile


def _display_methodology_card(methodology, detailed: bool = False):
    """Display methodology information in formatted panel."""
    content = []
    content.append(f"[bold]{methodology.name}[/bold]")
    content.append(f"Version: {methodology.version}")
    content.append(f"ID: [cyan]{methodology.id}[/cyan]")
    content.append(f"\n{methodology.philosophy.one_line_description}")

    if detailed:
        content.append(f"\n[bold]Core Logic:[/bold]")
        content.append(methodology.philosophy.core_logic)

        content.append(f"\n[bold]Assumptions ({len(methodology.assumptions)}):[/bold]")
        for i, assumption in enumerate(methodology.assumptions, 1):
            content.append(f"{i}. {assumption.expectation} ([yellow]{assumption.criticality}[/yellow])")

        content.append(f"\n[bold]Safety Gates ({len(methodology.safety_gates.exclusion_criteria)}):[/bold]")
        blocking = sum(
            1 for c in methodology.safety_gates.exclusion_criteria if c.severity.value == "blocking"
        )
        warning = len(methodology.safety_gates.exclusion_criteria) - blocking
        content.append(f"  • Blocking: {blocking}")
        content.append(f"  • Warning: {warning}")

        content.append(f"\n[bold]Base Fragility Score:[/bold] {methodology.risk_profile.fragility_score}")

    panel = Panel(
        "\n".join(content),
        title="Methodology Model Card",
        border_style="cyan",
    )
    console.print(panel)


def _display_validation_result(validator: MethodologyValidator, result):
    """Display validation result with color coding and formatting."""
    console.print()

    # Status panel
    if result.approved and not result.warnings:
        status = "[bold green]✅ APPROVED[/bold green]"
        status_detail = "All safety gates passed. Methodology is appropriate for current athlete state."
        border_color = "green"
    elif result.approved and result.warnings:
        status = "[bold yellow]⚠️  APPROVED WITH WARNINGS[/bold yellow]"
        status_detail = f"{len(result.warnings)} non-critical warning(s) identified."
        border_color = "yellow"
    else:
        status = "[bold red]⛔ REFUSED[/bold red]"
        blocking_count = sum(
            1
            for v in result.refusal_response.violations
            if v.severity.value == "blocking"
        )
        status_detail = f"{blocking_count} blocking condition(s) detected. Plan generation refused."
        border_color = "red"

    console.print(
        Panel(
            f"{status}\n\n{status_detail}",
            title="Validation Result",
            border_style=border_color,
        )
    )

    # Show warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")

    # Show violations
    if not result.approved and result.refusal_response:
        console.print("\n[bold red]Blocking Violations:[/bold red]\n")

        for i, violation in enumerate(result.refusal_response.violations, 1):
            if violation.severity.value == "blocking":
                console.print(f"[bold]{i}. {violation.condition}[/bold]")
                bridge = validator.generate_refusal_bridge(violation)
                console.print(Panel(bridge, border_style="red", padding=(1, 2)))
                console.print()

    # Assumption summary
    console.print("\n[bold]Assumption Check Summary:[/bold]")
    passed = sum(1 for c in result.reasoning_trace.checks if c.passed)
    total = len(result.reasoning_trace.checks)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Assumption", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("User Value")
    table.add_column("Required")

    for check in result.reasoning_trace.checks:
        status_icon = "✅" if check.passed else "❌"
        table.add_row(
            check.assumption_key,
            status_icon,
            str(check.user_value),
            str(check.threshold) if check.threshold else "N/A",
        )

    console.print(table)
    console.print(f"\n[bold]Result:[/bold] {passed}/{total} assumptions satisfied")


if __name__ == "__main__":
    app()
