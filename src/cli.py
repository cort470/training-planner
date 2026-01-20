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
from src.fragility import FragilityCalculator, FragilityResult
from src.planner import TrainingPlanGenerator
from src.sensitivity import SensitivityAnalyzer, SensitivityResult
from src.plan_schemas import TrainingPlan, IntensityZone
from rich import box

# Initialize Typer app and Rich console
app = typer.Typer(
    help="Human-in-the-Loop Training Planner - Transparent, interpretable training guidance"
)
console = Console()


# ===== DISPLAY HELPER FUNCTIONS =====


def _display_fragility_summary(result: FragilityResult, detailed: bool = False):
    """
    Display fragility score with color-coded interpretation and breakdown.

    Args:
        result: FragilityResult from calculator
        detailed: If True, shows additional details and explanations
    """
    # Color-code by risk level
    score = result.score
    if score < 0.4:
        color = "green"
    elif score < 0.6:
        color = "yellow"
    elif score < 0.8:
        color = "orange"
    else:
        color = "red"

    console.print(f"\n[bold]Fragility Score: [{color}]{score:.2f}[/{color}] "
                  f"({result.interpretation})[/bold]\n")

    # Breakdown table
    table = Table(title="Fragility Score Breakdown", box=box.ROUNDED)
    table.add_column("Factor", style="cyan")
    table.add_column("Contribution", justify="right", style="yellow")

    for factor, contribution in result.breakdown.items():
        factor_name = factor.replace("_", " ").title()
        table.add_row(factor_name, f"{contribution:+.3f}")

    console.print(table)

    # Recommendations
    if result.recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in result.recommendations:
            console.print(f"  • {rec}")


def _display_plan_summary(plan: TrainingPlan):
    """
    Display training plan summary with intensity distribution and phases.

    Args:
        plan: TrainingPlan object
    """
    console.print(f"\n✓ Generated [green]{plan.plan_duration_weeks}-week plan[/green]")
    console.print(f"  Start: {plan.plan_start_date}")
    console.print(f"  Fragility: {plan.fragility_score:.2f}")

    # Intensity distribution
    intensity_dist = plan.calculate_intensity_distribution()
    console.print("\n[bold]Intensity Distribution:[/bold]")
    console.print(f"  Low (Z1-Z2):  {intensity_dist.low_intensity_percent:.1f}%")
    console.print(f"  Threshold (Z3): {intensity_dist.threshold_percent:.1f}%")
    console.print(f"  High (Z4-Z5): {intensity_dist.high_intensity_percent:.1f}%")

    # Phase breakdown
    phase_breakdown = plan.get_phase_breakdown()
    console.print("\n[bold]Phase Distribution:[/bold]")
    for phase, weeks in phase_breakdown.items():
        console.print(f"  {phase}: {weeks} weeks")

    # Sample first week (first 3 sessions)
    if plan.weeks:
        first_week = plan.weeks[0]
        console.print(f"\n[bold]Sample Week {first_week.week_number} ({first_week.phase.value}):[/bold]")
        for session in first_week.sessions[:3]:
            desc_short = session.description[:55] + "..." if len(session.description) > 55 else session.description
            console.print(f"  {session.day.value}: {desc_short}")
            console.print(f"    Zone: {session.primary_zone.value}, Duration: {session.duration_minutes}min")


def _display_sensitivity_result(scenario: SensitivityResult):
    """
    Display sensitivity analysis scenario results with deltas.

    Args:
        scenario: SensitivityResult from analyzer
    """
    console.print(f"\n[bold]SCENARIO RESULTS[/bold]")
    console.print(f"Modified: {scenario.modified_assumption} "
                  f"({scenario.original_value} → {scenario.new_value})\n")

    # Fragility change
    if scenario.new_fragility is not None and scenario.original_fragility is not None:
        delta = scenario.fragility_delta
        delta_color = "green" if delta < 0 else "red"

        console.print(f"Fragility: {scenario.original_fragility:.2f} → "
                      f"{scenario.new_fragility:.2f} "
                      f"([{delta_color}]Δ {delta:+.3f}[/{delta_color}])")

    # Plan adjustments
    if scenario.plan_adjustments:
        console.print("\n[bold]Plan Adjustments:[/bold]")
        adj = scenario.plan_adjustments
        if adj.hi_sessions_per_week_delta != 0:
            console.print(f"  HI Sessions: {adj.hi_sessions_per_week_delta:+.1f}/week")
        if adj.volume_delta_percent != 0:
            console.print(f"  Volume: {adj.volume_delta_percent:+.1f}%")

    # Validation change
    val_changed = "changed" if scenario.validation_changed else "unchanged"
    console.print(f"\nValidation: {scenario.new_validation_status} ({val_changed})")


# ===== CLI COMMANDS =====


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


@app.command()
def analyze_fragility(
    profile: Path = typer.Option(
        ...,
        "--profile",
        "-p",
        help="Path to user profile JSON file",
        exists=True,
    ),
    methodology: Path = typer.Option(
        Path("models/methodology_polarized.json"),
        "--methodology",
        "-m",
        help="Path to methodology JSON file",
        exists=True,
    ),
):
    """
    Standalone fragility score analysis with detailed breakdown.
    """
    console.print("\n[bold cyan]Fragility Analysis[/bold cyan]\n")

    # Load methodology
    try:
        validator = MethodologyValidator.from_file(methodology)
    except Exception as e:
        console.print(f"[red]✗ Failed to load methodology: {e}[/red]")
        raise typer.Exit(1)

    # Load profile
    try:
        with open(profile) as f:
            user_profile = UserProfile(**json.load(f))
    except Exception as e:
        console.print(f"[red]✗ Failed to load profile: {e}[/red]")
        raise typer.Exit(1)

    # Calculate fragility
    calculator = FragilityCalculator(validator.methodology)
    fragility_result = calculator.calculate(user_profile)

    # Display detailed breakdown
    _display_fragility_summary(fragility_result, detailed=True)
    console.print()


@app.command()
def generate_plan(
    profile: Path = typer.Option(
        ...,
        "--profile",
        "-p",
        help="Path to user profile JSON file",
        exists=True,
    ),
    methodology: Path = typer.Option(
        Path("models/methodology_polarized.json"),
        "--methodology",
        "-m",
        help="Path to methodology JSON file",
        exists=True,
    ),
    save_plan: bool = typer.Option(
        True,
        "--save-plan/--no-save",
        help="Save plan to JSON file",
    ),
    save_trace: bool = typer.Option(
        True,
        "--save-trace/--no-trace",
        help="Save reasoning trace to file",
    ),
):
    """
    Generate training plan after validation.

    Workflow:
    1. Validate user profile
    2. Calculate fragility score
    3. Generate training plan
    4. Display summary
    5. Save plan and reasoning trace
    """
    console.print("\n[bold cyan]Training Plan Generator[/bold cyan]\n")

    # Load methodology
    try:
        validator = MethodologyValidator.from_file(methodology)
        console.print(f"✓ Loaded: [green]{validator.methodology.name}[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to load methodology: {e}[/red]")
        raise typer.Exit(1)

    # Load profile
    try:
        with open(profile) as f:
            user_profile = UserProfile(**json.load(f))
        console.print(f"✓ Loaded: [green]{user_profile.athlete_id}[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to load profile: {e}[/red]")
        raise typer.Exit(1)

    # Validate
    console.print("[bold]Step 1: Validation[/bold]")
    result = validator.validate(user_profile)

    if not result.approved:
        console.print("[red]✗ Validation failed. Cannot generate plan.[/red]\n")
        _display_validation_result(validator, result)
        raise typer.Exit(1)

    console.print("[green]✓ Validation: APPROVED[/green]\n")

    # Calculate fragility
    console.print("[bold]Step 2: Fragility Score[/bold]")
    calculator = FragilityCalculator(validator.methodology)
    fragility_result = calculator.calculate(user_profile)
    _display_fragility_summary(fragility_result)

    # Generate plan
    console.print("\n[bold]Step 3: Plan Generation[/bold]")
    generator = TrainingPlanGenerator(validator.methodology, result)
    plan = generator.generate(user_profile)

    # Display plan summary
    _display_plan_summary(plan)

    # Save plan
    if save_plan:
        plan_dir = Path("plans")
        plan_dir.mkdir(exist_ok=True)
        plan_path = plan_dir / f"plan_{user_profile.athlete_id}_{date.today().strftime('%Y%m%d')}.json"

        with open(plan_path, "w") as f:
            json.dump(plan.model_dump(mode="json"), f, indent=2, default=str)

        console.print(f"\n✓ Plan saved: [cyan]{plan_path}[/cyan]")

    # Save trace
    if save_trace:
        trace_dir = Path("reasoning_logs")
        trace_path = save_trace_from_result(result, trace_dir, format="markdown")
        console.print(f"✓ Trace saved: [cyan]{trace_path}[/cyan]")

    console.print()


@app.command()
def what_if(
    profile: Path = typer.Option(
        ...,
        "--profile",
        "-p",
        help="Path to user profile JSON file",
        exists=True,
    ),
    methodology: Path = typer.Option(
        Path("models/methodology_polarized.json"),
        "--methodology",
        "-m",
        help="Path to methodology JSON file",
        exists=True,
    ),
):
    """
    Interactive sensitivity analysis ("what-if" scenarios).

    Explore how changes to assumptions affect fragility scores and training plans.
    """
    console.print("\n[bold cyan]Sensitivity Analysis[/bold cyan]\n")

    # Load methodology
    try:
        validator = MethodologyValidator.from_file(methodology)
    except Exception as e:
        console.print(f"[red]✗ Failed to load methodology: {e}[/red]")
        raise typer.Exit(1)

    # Load profile
    try:
        with open(profile) as f:
            user_profile = UserProfile(**json.load(f))
    except Exception as e:
        console.print(f"[red]✗ Failed to load profile: {e}[/red]")
        raise typer.Exit(1)

    # Validate baseline
    baseline_result = validator.validate(user_profile)

    # Calculate baseline fragility
    calculator = FragilityCalculator(validator.methodology)
    baseline_fragility = calculator.calculate(user_profile)

    # Generate baseline plan if approved
    baseline_plan = None
    if baseline_result.approved:
        generator = TrainingPlanGenerator(validator.methodology, baseline_result)
        baseline_plan = generator.generate(user_profile)

    # Show baseline state
    console.print("[bold]Baseline State:[/bold]")
    console.print(f"  Sleep: {user_profile.current_state.sleep_hours} hrs")
    console.print(f"  Stress: {user_profile.current_state.stress_level.value}")
    console.print(f"  Volume: {user_profile.current_state.weekly_volume_hours} hrs/week")
    console.print(f"  F-Score: {baseline_fragility.score:.2f} ({baseline_fragility.interpretation})")

    if baseline_plan:
        # Calculate average HI sessions per week
        total_hi_sessions = 0
        for week in baseline_plan.weeks:
            hi_sessions = len([
                s for s in week.sessions
                if s.primary_zone in [IntensityZone.ZONE_4, IntensityZone.ZONE_5]
            ])
            total_hi_sessions += hi_sessions
        avg_hi = total_hi_sessions / len(baseline_plan.weeks)
        console.print(f"  HI Sessions: {avg_hi:.1f}/week")

    console.print()

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        validator.methodology,
        user_profile,
        baseline_result,
        baseline_plan,
    )

    # Interactive loop
    scenario_count = 0
    while True:
        assumption = Prompt.ask(
            "\nWhat assumption would you like to modify?",
            choices=["sleep_hours", "stress_level", "weekly_volume_hours", "injury_status", "exit"],
        )

        if assumption == "exit":
            break

        # Get current value
        current_value = getattr(user_profile.current_state, assumption)

        # Prompt for new value
        new_value_str = Prompt.ask(f"Enter new {assumption} value (current: {current_value})")

        # Parse based on type
        try:
            if assumption in ["sleep_hours", "weekly_volume_hours"]:
                new_value = float(new_value_str)
            elif assumption == "stress_level":
                new_value = StressLevel(new_value_str)
            elif assumption == "injury_status":
                new_value = new_value_str.lower() in ["true", "yes", "1"]
            else:
                new_value = new_value_str

            # Run scenario
            console.print("\n[bold]Analyzing scenario...[/bold]")
            scenario_result = analyzer.modify_assumption(f"current_state.{assumption}", new_value)

            # Display results
            _display_sensitivity_result(scenario_result)

            scenario_count += 1

        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            continue

        # Ask to continue
        if not Confirm.ask("\nRun another scenario?", default=True):
            break

    console.print(f"\n[dim]Summary: Explored {scenario_count} scenario(s)[/dim]\n")


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
