# Usage Guide: Human-in-the-Loop Training Planner

This guide demonstrates how to use the training planner system for validation, plan generation, and sensitivity analysis.

## Table of Contents

1. [Quick Start](#quick-start)
2. [User Profile Validation](#user-profile-validation)
3. [Fragility Score Analysis](#fragility-score-analysis)
4. [Training Plan Generation](#training-plan-generation)
5. [Sensitivity Analysis](#sensitivity-analysis)
6. [Understanding Results](#understanding-results)
7. [Common Scenarios](#common-scenarios)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd training-planner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### First Validation

```bash
# Validate a sample profile
python3 -m src.cli validate --profile tests/fixtures/test_user_valid.json
```

You should see output like:
```
✓ Loaded methodology: Polarized 80/20 (v1.0.0)
✓ Loaded profile: test_athlete_001

Validation Result: APPROVED ✓

Fragility Score: 0.42 (Moderate Risk)

Reasoning trace saved to: reasoning_logs/trace_test_athlete_001_20260120.json
```

## User Profile Validation

### Using CLI

#### Option 1: Validate Existing Profile

```bash
python3 -m src.cli validate --profile path/to/profile.json
```

#### Option 2: Interactive Profile Creation

```bash
python3 -m src.cli validate
```

This will prompt you for all required information:
- Athlete ID
- Current state (sleep, stress, volume, etc.)
- Training history
- Goals (race date, distance)
- Constraints (available days, session duration)
- Preferences (intensity distribution, rest days)

#### Option 3: View Methodology Details

```bash
python3 -m src.cli methodology --show models/methodology_polarized.json
```

### Using Python API

```python
from pathlib import Path
import json
from src.validator import MethodologyValidator
from src.schemas import UserProfile

# Load methodology
validator = MethodologyValidator.from_file(
    Path("models/methodology_polarized.json")
)

# Load user profile
with open("path/to/profile.json") as f:
    user_profile = UserProfile(**json.load(f))

# Validate
result = validator.validate(user_profile)

# Check result
if result.approved:
    print("✓ Validation passed!")
    print(f"Result: {result.reasoning_trace.result}")
else:
    print("✗ Validation refused")
    print(f"Reason: {result.reasoning_trace.result}")

    # Show safety gate violations
    for gate in result.reasoning_trace.safety_gates:
        print(f"\nGate: {gate.gate_id}")
        print(f"  Condition: {gate.condition}")
        print(f"  Status: {gate.status}")
        print(f"  Reasoning: {gate.reasoning}")
        if gate.recommendation:
            print(f"  Recommendation: {gate.recommendation}")
```

### Understanding Validation Results

#### Approved ✓
All safety gates passed. The system will:
- Calculate fragility score
- Proceed to plan generation if requested
- Save reasoning trace

#### Refused ✗
One or more safety gates failed. Common reasons:
- Active injury
- Sleep below threshold (< 6.5 hours for 7+ days)
- High stress with insufficient recovery
- Volume too high without consistency
- Recent illness with insufficient recovery

Each refusal includes:
- Specific gate that failed
- Clear reasoning
- Actionable recommendation

#### Warning ⚠
Minor concerns detected but not blocking. Examples:
- Slightly suboptimal sleep (6.5-7.0 hours)
- Moderate stress levels
- Volume at upper boundary

## Fragility Score Analysis

### What is Fragility Score?

The Fragility Score (F-Score) is a value from 0.0 to 1.0 that quantifies training plan risk:

- **0.0-0.4:** Low Risk (robust, can handle normal training)
- **0.4-0.6:** Moderate Risk (reduce intensity slightly)
- **0.6-0.8:** High Risk (significant caution needed)
- **0.8-1.0:** Critical Risk (minimal intensity only)

### Calculating Fragility Score

```python
from src.fragility import FragilityCalculator

# After validation passes
calculator = FragilityCalculator(validator.methodology)
fragility_result = calculator.calculate(user_profile)

print(f"Fragility Score: {fragility_result.score:.2f}")
print(f"Interpretation: {fragility_result.interpretation}")

# View breakdown
print("\nContributing Factors:")
for factor, contribution in fragility_result.breakdown.items():
    print(f"  {factor}: {contribution:.3f}")

# Get recommendations
print("\nRecommendations:")
for rec in fragility_result.recommendations:
    print(f"  • {rec}")
```

### Example Output

```
Fragility Score: 0.52
Interpretation: Moderate Risk

Contributing Factors:
  sleep_deviation: 0.028
  stress_multiplier: 0.036
  volume_variance: 0.000
  intensity_frequency: 0.032
  recovery_quality: 0.030

Recommendations:
  • Increase sleep to 7.5+ hours to reduce fragility
  • Monitor HRV trend for early fatigue detection
  • Consider reducing high-intensity frequency to 2 sessions/week
```

## Training Plan Generation

### Prerequisites

1. User profile must pass validation
2. Methodology must be loaded
3. All required profile fields must be present

### Generating a Plan

```python
from src.planner import TrainingPlanGenerator

# After successful validation
generator = TrainingPlanGenerator(
    methodology=validator.methodology,
    validation_result=result  # Must be approved
)

# Generate plan
plan = generator.generate(user_profile)

# Plan details
print(f"Plan Duration: {plan.plan_duration_weeks} weeks")
print(f"Total Weeks: {len(plan.weeks)}")
print(f"Fragility Score: {plan.fragility_score:.2f}")
print(f"Start Date: {plan.plan_start_date}")

# Analyze plan
intensity_dist = plan.calculate_intensity_distribution()
print(f"\nIntensity Distribution:")
print(f"  Low Intensity (Z1-Z2): {intensity_dist.low_intensity_percent:.1f}%")
print(f"  Threshold (Z3): {intensity_dist.threshold_percent:.1f}%")
print(f"  High Intensity (Z4-Z5): {intensity_dist.high_intensity_percent:.1f}%")

# Save plan
import json
with open(f"plans/plan_{user_profile.athlete_id}.json", "w") as f:
    json.dump(plan.model_dump(mode="json"), f, indent=2, default=str)
```

### Plan Structure

Each plan contains:
- **Weeks:** List of TrainingWeek objects
- **Sessions:** Daily training sessions with:
  - Day of week
  - Session type (run, bike, swim, brick, etc.)
  - Primary intensity zone
  - Duration in minutes
  - Detailed description
- **Phase:** Current training phase (base/build/peak/taper)
- **Volume:** Total weekly training hours

### Fragility-Based Adjustments

The planner automatically adjusts based on F-Score:

| F-Score Range | HI Sessions/Week | Adjustments |
|---------------|------------------|-------------|
| 0.0-0.4 | 3 | Normal progression |
| 0.4-0.6 | 2 | Reduced HI frequency |
| 0.6-0.8 | 1 | Minimal HI, extended base |
| 0.8-1.0 | 0-1 | Recovery focus |

### Viewing Plan Details

```python
# Iterate through weeks
for week in plan.weeks:
    print(f"\nWeek {week.week_number} ({week.phase.value})")
    print(f"Volume: {week.total_volume_hours:.1f} hours")

    for session in week.sessions:
        print(f"  {session.day.value}: {session.description}")
        print(f"    Type: {session.session_type.value}")
        print(f"    Zone: {session.primary_zone.value}")
        print(f"    Duration: {session.duration_minutes} min")

# Get phase breakdown
phase_breakdown = plan.get_phase_breakdown()
print("\nPhase Distribution:")
for phase, weeks in phase_breakdown.items():
    print(f"  {phase}: {weeks} weeks")

# Get average weekly volume
avg_volume = plan.get_average_weekly_volume()
print(f"\nAverage Weekly Volume: {avg_volume:.1f} hours")
```

## Sensitivity Analysis

Sensitivity analysis lets you explore "what-if" scenarios to see how changes affect validation, fragility, and plans.

### Creating an Analyzer

```python
from src.sensitivity import SensitivityAnalyzer

# Create analyzer with baseline state
analyzer = SensitivityAnalyzer(
    methodology=validator.methodology,
    baseline_profile=user_profile,
    baseline_validation=result,
    baseline_plan=plan  # Optional, needed for plan comparisons
)
```

### Modifying Assumptions

#### Example 1: Increase Sleep

```python
# Modify sleep from 6.5 to 7.5 hours
scenario = analyzer.modify_assumption(
    "current_state.sleep_hours",
    7.5
)

print(f"Original: {scenario.original_value} hours")
print(f"New: {scenario.new_value} hours")
print(f"Fragility: {scenario.original_fragility:.2f} → {scenario.new_fragility:.2f}")
print(f"Change: {scenario.fragility_delta:+.3f}")

if scenario.plan_adjustments:
    print(f"HI Sessions: {scenario.plan_adjustments.hi_sessions_per_week_delta:+.1f}/week")
```

Output:
```
Original: 6.5 hours
New: 7.5 hours
Fragility: 0.52 → 0.45
Change: -0.070
HI Sessions: +1.0/week
```

#### Example 2: Change Stress Level

```python
from src.schemas import StressLevel

scenario = analyzer.modify_assumption(
    "current_state.stress_level",
    StressLevel.HIGH
)

print(f"Original: {scenario.original_value}")
print(f"New: {scenario.new_value}")
print(f"Validation changed: {scenario.validation_changed}")
print(f"New status: {scenario.new_validation_status}")
```

#### Example 3: Add Injury

```python
scenario = analyzer.modify_assumption(
    "current_state.injury_status",
    True
)

if scenario.validation_changed:
    print("⚠ Validation status changed to REFUSED")
    print("\nNew violations:")
    for violation in scenario.new_violations:
        print(f"  • {violation}")
```

### Available Modification Paths

You can modify any field in the user profile using dot notation:

**Current State:**
- `current_state.sleep_hours`
- `current_state.injury_status`
- `current_state.stress_level`
- `current_state.weekly_volume_hours`
- `current_state.volume_consistency_weeks`
- `current_state.recent_illness`
- `current_state.hrv_trend`
- `current_state.resting_heart_rate`

**Goals:**
- `goals.weeks_to_race`
- `goals.race_distance`
- `goals.primary_goal`

**Constraints:**
- `constraints.available_training_days`
- `constraints.max_session_duration_hours`

### Comparing Multiple Scenarios

```python
# Test multiple sleep values
sleep_values = [6.0, 6.5, 7.0, 7.5, 8.0]
results = []

for sleep in sleep_values:
    scenario = analyzer.modify_assumption("current_state.sleep_hours", sleep)
    results.append({
        "sleep": sleep,
        "fragility": scenario.new_fragility,
        "validation": scenario.new_validation_status,
    })

# Display comparison
import pandas as pd
df = pd.DataFrame(results)
print(df)
```

Output:
```
   sleep  fragility validation
0    6.0       0.58   approved
1    6.5       0.52   approved
2    7.0       0.47   approved
3    7.5       0.45   approved
4    8.0       0.42   approved
```

## Understanding Results

### Reasoning Trace

Every validation produces a reasoning trace that documents:
- All assumptions checked
- Safety gates evaluated
- Fragility calculation (if approved)
- Plan generation decisions (if generated)

```python
# Access reasoning trace
trace = result.reasoning_trace

# View all checked assumptions
for assumption in trace.assumptions:
    print(f"\n{assumption.parameter}")
    print(f"  Required: {assumption.required_value}")
    print(f"  Actual: {assumption.actual_value}")
    print(f"  Status: {assumption.status}")

# View safety gates
for gate in trace.safety_gates:
    print(f"\n{gate.gate_id}")
    print(f"  Status: {gate.status}")
    print(f"  Reasoning: {gate.reasoning}")
```

### Exporting Results

```python
# Export as JSON
from src.trace import save_trace_from_result

trace_path = save_trace_from_result(
    result,
    output_dir=Path("reasoning_logs"),
    format="json"
)
print(f"Trace saved to: {trace_path}")

# Export as Markdown (human-readable)
trace_path = save_trace_from_result(
    result,
    output_dir=Path("reasoning_logs"),
    format="markdown"
)
```

## Common Scenarios

### Scenario 1: First-Time User

```python
# 1. Create profile
from src.schemas import UserProfile, CurrentState, Goals, Constraints, Preferences
from datetime import date

profile = UserProfile(
    athlete_id="new_athlete_001",
    profile_date=date.today(),
    current_state=CurrentState(
        sleep_hours=7.5,
        injury_status=False,
        stress_level=StressLevel.LOW,
        weekly_volume_hours=8.0,
        volume_consistency_weeks=4,
        recent_illness=False,
        hrv_trend=HRVTrend.STABLE,
    ),
    training_history={
        "years_training": 2,
        "recent_races": []
    },
    goals=Goals(
        primary_goal=PrimaryGoal.RACE_PERFORMANCE,
        race_date=date(2026, 6, 15),
        race_distance=RaceDistance.OLYMPIC,
        weeks_to_race=20,
    ),
    constraints=Constraints(
        available_training_days=5,
        max_session_duration_hours=2.0,
    ),
    preferences=Preferences(
        preferred_intensity_distribution="polarized",
        long_workout_day=Weekday.SATURDAY,
        rest_day=Weekday.SUNDAY,
    ),
)

# 2. Validate
result = validator.validate(profile)

# 3. Calculate fragility
if result.approved:
    fragility = calculator.calculate(profile)
    print(f"Your fragility score: {fragility.score:.2f}")

# 4. Generate plan
if result.approved:
    plan = generator.generate(profile)
    print(f"Generated {len(plan.weeks)}-week plan")
```

### Scenario 2: Injury Recovery

```python
# User is recovering from injury
profile.current_state.injury_status = True
profile.current_state.recent_illness = False

result = validator.validate(profile)

if not result.approved:
    print("Validation refused due to injury")
    for gate in result.reasoning_trace.safety_gates:
        if gate.status == "violated":
            print(f"Recommendation: {gate.recommendation}")
```

### Scenario 3: High Stress Period

```python
# User entering high-stress period
profile.current_state.stress_level = StressLevel.HIGH
profile.current_state.sleep_hours = 6.5

result = validator.validate(profile)
fragility = calculator.calculate(profile)

print(f"Fragility with high stress: {fragility.score:.2f}")

# Compare with reduced stress
analyzer = SensitivityAnalyzer(
    validator.methodology, profile, result, None
)
scenario = analyzer.modify_assumption(
    "current_state.stress_level",
    StressLevel.MODERATE
)

print(f"Fragility with moderate stress: {scenario.new_fragility:.2f}")
print(f"Improvement: {-scenario.fragility_delta:.3f}")
```

### Scenario 4: Short-Notice Race

```python
# Only 4 weeks to race
profile.goals.weeks_to_race = 4

result = validator.validate(profile)
if result.approved:
    plan = generator.generate(profile)

    # Check phase distribution for short plan
    phases = plan.get_phase_breakdown()
    print(f"Phase distribution: {phases}")

    # Verify taper included
    last_week = plan.weeks[-1]
    print(f"Final week phase: {last_week.phase.value}")
    print(f"Final week volume: {last_week.total_volume_hours:.1f} hours")
```

## Troubleshooting

### Validation Fails

**Problem:** Profile validation refused

**Solutions:**
1. Check reasoning trace for specific gate violations
2. Review recommendations for each violated gate
3. Use sensitivity analysis to explore adjustments
4. Modify profile and re-validate

### Fragility Score Too High

**Problem:** F-Score > 0.6 (high risk)

**Solutions:**
1. Review fragility breakdown to identify main contributors
2. Check recommendations in fragility result
3. Use sensitivity analysis to test improvements:
   - Increase sleep
   - Reduce stress
   - Improve volume consistency
   - Allow more recovery time

### Plan Generation Issues

**Problem:** Plan doesn't match expectations

**Check:**
1. Fragility score - high scores reduce intensity
2. Available training days - affects session distribution
3. Volume consistency - affects phase progression
4. Weeks to race - affects phase allocation

### Understanding Refusals

The system refuses for safety. This is intentional. Common refusals:

1. **Active Injury**
   - Recommendation: Seek medical clearance
   - Timeline: Wait for full recovery

2. **Insufficient Sleep**
   - Recommendation: Increase to 7+ hours
   - Timeline: 7+ days of consistent sleep

3. **High Stress + Low Recovery**
   - Recommendation: Reduce stress or improve recovery
   - Timeline: Until HRV stabilizes

4. **Volume Too High**
   - Recommendation: Build consistency first
   - Timeline: 4-8 weeks at lower volume

## Phase 3: Enhanced CLI Commands

### Generate Training Plan Command

The `generate-plan` command provides a complete end-to-end workflow:

```bash
python3 -m src.cli generate-plan --profile tests/fixtures/test_user_valid.json
```

**What it does:**
1. Validates the user profile against methodology
2. Calculates fragility score with breakdown
3. Generates complete training plan
4. Displays plan summary (intensity, phases, sample week)
5. Saves plan JSON to `plans/` directory
6. Saves enhanced reasoning trace to `reasoning_logs/`

**Example Output:**
```
Training Plan Generator

✓ Loaded: Polarized 80/20 Training
✓ Loaded: test_athlete_001

Step 1: Validation
✓ Validation: APPROVED

Step 2: Fragility Score
Fragility Score: 0.44 (Moderate Risk)
[Detailed breakdown table]

Step 3: Plan Generation
✓ Generated 12-week plan
  Intensity: 80.0% Z1-2, 20.0% Z4-5
  HI Sessions: 3.0/week

✓ Plan saved: plans/plan_test_athlete_001_20260120.json
```

### Analyze Fragility Command

Standalone fragility analysis without full plan generation:

```bash
python3 -m src.cli analyze-fragility --profile tests/fixtures/test_user_valid.json
```

Shows:
- Color-coded F-Score (green/yellow/orange/red)
- Detailed breakdown by penalty factor
- Specific recommendations for improvement

### What-If Analysis Command

Interactive sensitivity analysis to explore scenarios:

```bash
python3 -m src.cli what-if --profile tests/fixtures/test_user_moderate_fragility.json
```

**Interactive Flow:**
```
Baseline State:
  Sleep: 6.5 hrs
  Stress: moderate
  F-Score: 0.52 (Moderate Risk)
  HI Sessions: 2.0/week

What assumption would you like to modify?
  [1] sleep_hours
  [2] stress_level
  [3] weekly_volume_hours
  [4] injury_status
  [5] exit

> 1

Enter new sleep_hours value (current: 6.5): 7.5

SCENARIO RESULTS
Modified: sleep_hours (6.5 → 7.5)
Fragility: 0.52 → 0.45 (Δ -0.070)
Plan Adjustments:
  HI Sessions: +1.0/week
```

**Supported Modifications:**
- `sleep_hours` - Average nightly sleep
- `stress_level` - low, moderate, high
- `weekly_volume_hours` - Training volume
- `injury_status` - Active injury status

### Command Options

All commands support:
- `--methodology` or `-m`: Path to methodology file (default: models/methodology_polarized.json)
- `--profile` or `-p`: Path to user profile JSON

`generate-plan` specific options:
- `--save-plan/--no-save`: Control plan file saving (default: save)
- `--save-trace/--no-trace`: Control trace saving (default: save)

## Additional Resources

- **API Documentation:** See docstrings in source files
- **Schema Reference:** [docs/schema_user_profile.json](docs/schema_user_profile.json)
- **Methodology Guide:** [docs/methodology_guide.md](docs/methodology_guide.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **CLI Reference:** Run `python3 -m src.cli --help` for all commands

## Getting Help

- Check reasoning traces for detailed explanations
- Review test fixtures for example profiles
- Open an issue for questions or bugs
- Consult [docs/prd_v3.txt](docs/prd_v3.txt) for design rationale
- Use `--help` flag on any command for usage details
