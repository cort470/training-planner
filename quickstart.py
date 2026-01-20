#!/usr/bin/env python3
"""
Quick start script to demonstrate the Human-in-the-Loop Training Planner.

This script shows the complete workflow:
1. Load methodology and user profile
2. Validate profile against methodology
3. Calculate fragility score
4. Generate training plan
5. Perform sensitivity analysis
"""

import json
from pathlib import Path
from datetime import date

from src.validator import MethodologyValidator
from src.schemas import UserProfile
from src.fragility import FragilityCalculator
from src.planner import TrainingPlanGenerator
from src.sensitivity import SensitivityAnalyzer

# Rich console for pretty output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def print_header(title: str):
    """Print a formatted header."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("=" * len(title))


def main():
    """Run the complete demonstration workflow."""
    console.print("\n[bold magenta]🏊 🚴 🏃 Human-in-the-Loop Training Planner[/bold magenta]")
    console.print("[dim]Demonstration of complete workflow[/dim]\n")

    # ===== STEP 1: Load Methodology =====
    print_header("Step 1: Load Methodology")

    methodology_path = Path("models/methodology_polarized.json")
    validator = MethodologyValidator.from_file(methodology_path)

    console.print(f"✓ Loaded: [green]{validator.methodology.name}[/green]")
    console.print(f"  Version: {validator.methodology.version}")
    console.print(f"  Safety Gates: {len(validator.methodology.safety_gates.exclusion_criteria)}")
    console.print(f"  Base Fragility: {validator.methodology.risk_profile.fragility_score}")

    # ===== STEP 2: Load User Profile =====
    print_header("Step 2: Load User Profile")

    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        user_profile = UserProfile(**json.load(f))

    console.print(f"✓ Loaded: [green]{user_profile.athlete_id}[/green]")
    console.print(f"  Sleep: {user_profile.current_state.sleep_hours} hours")
    console.print(f"  Stress: {user_profile.current_state.stress_level.value}")
    console.print(f"  Volume: {user_profile.current_state.weekly_volume_hours} hours/week")
    console.print(f"  Race: {user_profile.goals.race_distance.value} in {user_profile.goals.weeks_to_race} weeks")

    # ===== STEP 3: Validate Profile =====
    print_header("Step 3: Validate Profile")

    result = validator.validate(user_profile)

    if result.approved:
        console.print("[green]✓ Validation: APPROVED[/green]")
        console.print(f"  Result: {result.reasoning_trace.result}")
        console.print(f"  Assumptions Checked: {len(result.reasoning_trace.checks)}")
        console.print(f"  Safety Gates: All passed")
    else:
        console.print("[red]✗ Validation: REFUSED[/red]")
        console.print(f"  Reason: {result.reasoning_trace.result}")
        for gate in result.reasoning_trace.safety_gates:
            if gate.status == "violated":
                console.print(f"  - {gate.condition}: {gate.reasoning}")
        return

    # ===== STEP 4: Calculate Fragility Score =====
    print_header("Step 4: Calculate Fragility Score")

    calculator = FragilityCalculator(validator.methodology)
    fragility_result = calculator.calculate(user_profile)

    # Create fragility table
    table = Table(title="Fragility Score Breakdown", box=box.ROUNDED)
    table.add_column("Factor", style="cyan")
    table.add_column("Contribution", justify="right", style="yellow")

    for factor, contribution in fragility_result.breakdown.items():
        table.add_row(factor.replace("_", " ").title(), f"{contribution:.3f}")

    console.print(table)

    console.print(f"\n[bold]Final F-Score: {fragility_result.score:.2f}[/bold]")
    console.print(f"Interpretation: [yellow]{fragility_result.interpretation}[/yellow]")

    console.print("\n[bold]Recommendations:[/bold]")
    for rec in fragility_result.recommendations:
        console.print(f"  • {rec}")

    # ===== STEP 5: Generate Training Plan =====
    print_header("Step 5: Generate Training Plan")

    generator = TrainingPlanGenerator(validator.methodology, result)
    plan = generator.generate(user_profile)

    console.print(f"✓ Generated [green]{plan.plan_duration_weeks}-week plan[/green]")
    console.print(f"  Start Date: {plan.plan_start_date}")
    console.print(f"  Total Weeks: {len(plan.weeks)}")
    console.print(f"  Fragility Score: {plan.fragility_score:.2f}")

    # Intensity distribution
    intensity_dist = plan.calculate_intensity_distribution()
    console.print(f"\n[bold]Intensity Distribution:[/bold]")
    console.print(f"  Low Intensity (Z1-Z2): {intensity_dist.low_intensity_percent:.1f}%")
    console.print(f"  Threshold (Z3): {intensity_dist.threshold_percent:.1f}%")
    console.print(f"  High Intensity (Z4-Z5): {intensity_dist.high_intensity_percent:.1f}%")

    # Phase breakdown
    phase_breakdown = plan.get_phase_breakdown()
    console.print(f"\n[bold]Phase Distribution:[/bold]")
    for phase, weeks in phase_breakdown.items():
        console.print(f"  {phase}: {weeks} weeks")

    # Show first week
    first_week = plan.weeks[0]
    console.print(f"\n[bold]Sample Week (Week {first_week.week_number} - {first_week.phase.value}):[/bold]")
    for session in first_week.sessions[:3]:  # Show first 3 sessions
        console.print(f"  {session.day.value}: {session.description[:60]}...")
        console.print(f"    Zone: {session.primary_zone.value}, Duration: {session.duration_minutes}min")

    # Save plan
    plan_dir = Path("plans")
    plan_dir.mkdir(exist_ok=True)
    plan_path = plan_dir / f"demo_plan_{date.today().strftime('%Y%m%d')}.json"

    with open(plan_path, "w") as f:
        json.dump(plan.model_dump(mode="json"), f, indent=2, default=str)

    console.print(f"\n✓ Plan saved to: [cyan]{plan_path}[/cyan]")

    # ===== STEP 6: Sensitivity Analysis =====
    print_header("Step 6: Sensitivity Analysis")

    console.print("[dim]Testing 'what-if' scenarios...[/dim]\n")

    analyzer = SensitivityAnalyzer(
        validator.methodology,
        user_profile,
        result,
        plan
    )

    # Scenario 1: Increase sleep
    console.print("[bold]Scenario 1: Increase Sleep (7.5 → 8.0 hours)[/bold]")
    scenario1 = analyzer.modify_assumption("current_state.sleep_hours", 8.0)

    console.print(f"  Original Fragility: {scenario1.original_fragility:.2f}")
    console.print(f"  New Fragility: {scenario1.new_fragility:.2f}")
    console.print(f"  Change: {scenario1.fragility_delta:+.3f}")

    if scenario1.plan_adjustments and scenario1.plan_adjustments.hi_sessions_per_week_delta:
        console.print(f"  HI Sessions: {scenario1.plan_adjustments.hi_sessions_per_week_delta:+.1f}/week")

    # Scenario 2: Increase stress
    console.print("\n[bold]Scenario 2: High Stress Period[/bold]")
    from src.schemas import StressLevel
    scenario2 = analyzer.modify_assumption("current_state.stress_level", StressLevel.HIGH)

    console.print(f"  Original Fragility: {scenario2.original_fragility:.2f}")
    console.print(f"  New Fragility: {scenario2.new_fragility:.2f}")
    console.print(f"  Change: {scenario2.fragility_delta:+.3f}")
    console.print(f"  Validation Changed: {scenario2.validation_changed}")

    # Scenario 3: Reduce available days
    console.print("\n[bold]Scenario 3: Reduce Training Days (6 → 5)[/bold]")
    scenario3 = analyzer.modify_assumption("constraints.available_training_days", 5)

    console.print(f"  Original: {scenario3.original_value} days")
    console.print(f"  New: {scenario3.new_value} days")
    console.print(f"  Validation Status: {scenario3.new_validation_status}")

    # ===== COMPLETION =====
    console.print("\n")
    panel = Panel(
        "[green]✓[/green] Demonstration complete!\n\n"
        "The system successfully:\n"
        "  1. Validated user profile against methodology\n"
        "  2. Calculated fragility score\n"
        "  3. Generated personalized training plan\n"
        "  4. Performed sensitivity analysis\n\n"
        "All decisions are documented in reasoning traces.\n"
        "Check the plans/ and reasoning_logs/ directories.",
        title="[bold green]Success[/bold green]",
        border_style="green"
    )
    console.print(panel)

    console.print("\n[bold cyan]Next Steps:[/bold cyan]")
    console.print("  • Review the generated plan in plans/")
    console.print("  • Check reasoning traces in reasoning_logs/")
    console.print("  • Run CLI: python3 -m src.cli validate --profile <your-profile.json>")
    console.print("  • Read USAGE_GUIDE.md for more examples")
    console.print("  • Run tests: python3 -m pytest\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("\n[dim]Make sure you're in the training-planner directory[/dim]")
        console.print("[dim]and have installed dependencies: pip install -r requirements.txt[/dim]")
        raise
