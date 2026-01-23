"""
Tests for training plan generation.

Covers:
- Plan generation for approved validation
- Phase determination logic
- Intensity distribution (80/20)
- Fragility-based adjustments
- Volume calculations
- Session scheduling
"""

import json
from datetime import date
from pathlib import Path

import pytest

from src.plan_schemas import (
    HIGH_INTENSITY_ZONES,
    IntensityZone,
    THRESHOLD_ZONES,
    TrainingPhase,
    WeekType,
)
from src.planner import TrainingPlanGenerator
from src.schemas import MethodologyModelCard, UserProfile
from src.validator import MethodologyValidator


@pytest.fixture
def methodology():
    """Load the polarized methodology for testing."""
    methodology_path = Path("models/methodology_polarized.json")
    with open(methodology_path) as f:
        data = json.load(f)
    return MethodologyModelCard(**data)


@pytest.fixture
def validator(methodology):
    """Create validator instance."""
    return MethodologyValidator(methodology)


@pytest.fixture
def valid_user_12_week():
    """Load 12-week race scenario user."""
    profile_path = Path("tests/fixtures/test_user_12_week_race.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def valid_user_4_week():
    """Load 4-week race scenario user."""
    profile_path = Path("tests/fixtures/test_user_4_week_race.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def high_fragility_user():
    """Load high fragility user."""
    profile_path = Path("tests/fixtures/test_user_high_fragility.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


def test_generator_requires_approved_validation(methodology, validator, valid_user_12_week):
    """Test that generator raises error if validation not approved."""
    # Create refused validation by using an injured user
    refused_user = valid_user_12_week.model_copy(deep=True)
    refused_user.current_state.injury_status = True
    refused_user.current_state.injury_details = "Stress fracture"

    refused_result = validator.validate(refused_user)

    assert not refused_result.approved

    with pytest.raises(ValueError, match="Cannot generate plan for refused validation"):
        TrainingPlanGenerator(methodology, refused_result)


def test_plan_generation_success_12_week(methodology, validator, valid_user_12_week):
    """Test successful plan generation for 12-week scenario."""
    validation_result = validator.validate(valid_user_12_week)
    assert validation_result.approved

    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Verify plan structure
    assert plan.athlete_id == valid_user_12_week.athlete_id
    assert plan.methodology_id == methodology.id
    assert plan.plan_duration_weeks == 12
    assert len(plan.weeks) == 12
    assert plan.fragility_score >= 0.0
    assert plan.fragility_score <= 1.0

    # Verify weeks are sequential
    for i, week in enumerate(plan.weeks, start=1):
        assert week.week_number == i


def test_plan_generation_success_4_week(methodology, validator, valid_user_4_week):
    """Test successful plan generation for short 4-week scenario."""
    validation_result = validator.validate(valid_user_4_week)
    assert validation_result.approved

    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_4_week)

    # Verify plan structure
    assert plan.plan_duration_weeks == 4
    assert len(plan.weeks) == 4


def test_phase_distribution_12_week(methodology, validator, valid_user_12_week):
    """Test phase distribution for standard 12-week plan."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    phase_counts = plan.get_phase_breakdown()

    # 12-week plan should have: ~30% base, ~45% build, ~15% peak, ~10% taper
    # Expected: 3-4wk base, 5-6wk build, 2wk peak, 1-2wk taper
    assert phase_counts.get("base", 0) >= 3
    assert phase_counts.get("build", 0) >= 4
    assert phase_counts.get("peak", 0) >= 1
    assert phase_counts.get("taper", 0) >= 1

    # Total should equal 12
    assert sum(phase_counts.values()) == 12


def test_phase_distribution_4_week(methodology, validator, valid_user_4_week):
    """Test phase distribution for short 4-week plan."""
    validation_result = validator.validate(valid_user_4_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_4_week)

    phase_counts = plan.get_phase_breakdown()

    # 4-week plan should have all phases but shorter
    # Expected: 2wk base, 1wk build, 0-1wk peak, 1wk taper
    assert phase_counts.get("base", 0) >= 1
    assert phase_counts.get("taper", 0) >= 1

    # Total should equal 4
    assert sum(phase_counts.values()) == 4


def test_intensity_distribution_80_20(methodology, validator, valid_user_12_week):
    """Test that plan follows 80/20 intensity distribution."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    intensity_dist = plan.calculate_intensity_distribution()

    # 80/20 polarized: 80% low intensity, 20% high intensity
    # Allow ±5% tolerance
    assert intensity_dist.low_intensity_percent >= 75.0
    assert intensity_dist.low_intensity_percent <= 85.0

    assert intensity_dist.high_intensity_percent >= 15.0
    assert intensity_dist.high_intensity_percent <= 25.0

    # Zone 3 (threshold) should be minimized in polarized methodology
    assert intensity_dist.threshold_percent <= 5.0


def test_intensity_distribution_threshold_70_20_10():
    """Test that Threshold methodology follows 70/20/10 intensity distribution."""
    # Load Threshold methodology
    methodology_path = Path("models/methodology_threshold_70_20_10_v1.json")
    with open(methodology_path) as f:
        data = json.load(f)
    threshold_methodology = MethodologyModelCard(**data)

    # Load threshold user fixture
    profile_path = Path("tests/fixtures/test_user_threshold_12_week.json")
    with open(profile_path) as f:
        user_data = json.load(f)
    threshold_user = UserProfile(**user_data)

    # Validate and generate plan
    validator = MethodologyValidator(threshold_methodology)
    validation_result = validator.validate(threshold_user)
    assert validation_result.approved, "Threshold user should pass validation"

    generator = TrainingPlanGenerator(threshold_methodology, validation_result)
    plan = generator.generate(threshold_user)

    intensity_dist = plan.calculate_intensity_distribution()

    # 70/20/10 threshold: 70% low, 20% threshold (Z3), 10% high
    # Allow ±10% tolerance due to discrete session constraints and fragility adjustments
    assert intensity_dist.low_intensity_percent >= 60.0
    assert intensity_dist.low_intensity_percent <= 80.0

    # Z3 + Z4 combined should be 30% (±10% tolerance)
    combined_intensity = intensity_dist.threshold_percent + intensity_dist.high_intensity_percent
    assert combined_intensity >= 20.0
    assert combined_intensity <= 40.0

    # Z3 should be present (at least 10%)
    assert intensity_dist.threshold_percent >= 10.0


def test_intensity_distribution_pyramidal():
    """Test that Pyramidal methodology follows 77/15/8 intensity distribution."""
    # Load Pyramidal methodology
    methodology_path = Path("models/methodology_pyramidal_v1.json")
    with open(methodology_path) as f:
        data = json.load(f)
    pyramidal_methodology = MethodologyModelCard(**data)

    # Load pyramidal user fixture
    profile_path = Path("tests/fixtures/test_user_pyramidal_12_week.json")
    with open(profile_path) as f:
        user_data = json.load(f)
    pyramidal_user = UserProfile(**user_data)

    # Validate and generate plan
    validator = MethodologyValidator(pyramidal_methodology)
    validation_result = validator.validate(pyramidal_user)
    assert validation_result.approved, "Pyramidal user should pass validation"

    generator = TrainingPlanGenerator(pyramidal_methodology, validation_result)
    plan = generator.generate(pyramidal_user)

    intensity_dist = plan.calculate_intensity_distribution()

    # 77/15/8 pyramidal: 77% low, 15% threshold (Z3), 8% high
    # Allow ±10% tolerance due to discrete session constraints and fragility adjustments
    assert intensity_dist.low_intensity_percent >= 67.0
    assert intensity_dist.low_intensity_percent <= 87.0

    # Z3 + Z4 combined should be 23% (±10% tolerance)
    combined_intensity = intensity_dist.threshold_percent + intensity_dist.high_intensity_percent
    assert combined_intensity >= 13.0
    assert combined_intensity <= 33.0

    # Z3 should be present (at least 8%)
    assert intensity_dist.threshold_percent >= 8.0


def test_fragility_reduces_hi_frequency_high(methodology, validator, high_fragility_user):
    """Test that high fragility reduces HI session frequency."""
    validation_result = validator.validate(high_fragility_user)

    # Even if validation passes (warning), plan should be generated
    if not validation_result.approved:
        pytest.skip("High fragility user was refused validation")

    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(high_fragility_user)

    # High fragility (F-Score > 0.6) should result in 1 HI session/week
    # Check a build phase week (not taper)
    build_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.BUILD]

    if build_weeks:
        build_week = build_weeks[0]
        hi_sessions = [
            s
            for s in build_week.sessions
            if s.primary_zone in HIGH_INTENSITY_ZONES
        ]

        # High fragility should have 1-2 HI sessions max
        assert len(hi_sessions) <= 2


def test_fragility_normal_hi_frequency_low(methodology, validator, valid_user_12_week):
    """Test that low fragility allows normal HI session frequency."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Low-moderate fragility should have 2-3 HI sessions/week
    # Check a build phase LOAD week (not recovery weeks which have reduced HI)
    build_load_weeks = [
        w for w in plan.weeks
        if w.phase == TrainingPhase.BUILD and w.week_type == WeekType.LOAD
    ]

    if build_load_weeks:
        build_week = build_load_weeks[0]
        hi_sessions = [
            s
            for s in build_week.sessions
            if s.primary_zone in HIGH_INTENSITY_ZONES
        ]

        # Low fragility should have 2-3 HI sessions in load weeks
        assert len(hi_sessions) >= 2


def test_threshold_session_types():
    """Test that Threshold methodology includes Zone 3 threshold workouts."""
    # Load Threshold methodology
    methodology_path = Path("models/methodology_threshold_70_20_10_v1.json")
    with open(methodology_path) as f:
        data = json.load(f)
    threshold_methodology = MethodologyModelCard(**data)

    # Load threshold user fixture
    profile_path = Path("tests/fixtures/test_user_threshold_12_week.json")
    with open(profile_path) as f:
        user_data = json.load(f)
    threshold_user = UserProfile(**user_data)

    # Validate and generate plan
    validator = MethodologyValidator(threshold_methodology)
    validation_result = validator.validate(threshold_user)
    generator = TrainingPlanGenerator(threshold_methodology, validation_result)
    plan = generator.generate(threshold_user)

    # Check build/peak weeks for threshold sessions (TEMPO and THRESHOLD zones)
    intensity_weeks = [w for w in plan.weeks if w.phase in [TrainingPhase.BUILD, TrainingPhase.PEAK]]

    # Should have threshold sessions in at least some build/peak weeks
    threshold_session_count = 0
    for week in intensity_weeks:
        threshold_sessions = [s for s in week.sessions if s.primary_zone in THRESHOLD_ZONES]
        threshold_session_count += len(threshold_sessions)

    # Threshold methodology should have significant threshold work (at least 15% of sessions in build/peak)
    total_intensity_sessions = sum(len(week.sessions) for week in intensity_weeks)
    threshold_percentage = (threshold_session_count / total_intensity_sessions) * 100 if total_intensity_sessions > 0 else 0

    assert threshold_percentage >= 15.0, f"Threshold methodology should have ≥15% threshold sessions in build/peak, got {threshold_percentage:.1f}%"

    # Verify some session descriptions mention "threshold" or "tempo"
    threshold_descriptions = []
    for week in intensity_weeks:
        for session in week.sessions:
            if session.primary_zone in THRESHOLD_ZONES:
                threshold_descriptions.append(session.description.lower())

    assert any("threshold" in desc or "tempo" in desc for desc in threshold_descriptions), \
        "Threshold sessions should mention 'threshold' or 'tempo' in description"


def test_pyramidal_session_types():
    """Test that Pyramidal methodology includes balanced Z3 and Z4 workouts."""
    # Load Pyramidal methodology
    methodology_path = Path("models/methodology_pyramidal_v1.json")
    with open(methodology_path) as f:
        data = json.load(f)
    pyramidal_methodology = MethodologyModelCard(**data)

    # Load pyramidal user fixture
    profile_path = Path("tests/fixtures/test_user_pyramidal_12_week.json")
    with open(profile_path) as f:
        user_data = json.load(f)
    pyramidal_user = UserProfile(**user_data)

    # Validate and generate plan
    validator = MethodologyValidator(pyramidal_methodology)
    validation_result = validator.validate(pyramidal_user)
    generator = TrainingPlanGenerator(pyramidal_methodology, validation_result)
    plan = generator.generate(pyramidal_user)

    # Check build/peak weeks for balanced threshold and high-intensity distribution
    intensity_weeks = [w for w in plan.weeks if w.phase in [TrainingPhase.BUILD, TrainingPhase.PEAK]]

    threshold_session_count = 0
    hi_session_count = 0

    for week in intensity_weeks:
        threshold_sessions = [s for s in week.sessions if s.primary_zone in THRESHOLD_ZONES]
        hi_sessions = [s for s in week.sessions if s.primary_zone in HIGH_INTENSITY_ZONES]
        threshold_session_count += len(threshold_sessions)
        hi_session_count += len(hi_sessions)

    # Pyramidal should have both threshold and high-intensity work
    assert threshold_session_count > 0, "Pyramidal should include threshold sessions"
    assert hi_session_count > 0, "Pyramidal should include high-intensity sessions"

    # Threshold should be more frequent than VO2max (pyramidal pattern: more threshold than VO2max)
    # Ratio should be approximately 15% threshold vs 8% VO2max (roughly 2:1)
    # With discrete sessions, exact ratios may vary based on fragility and total session count
    total_intensity_sessions = threshold_session_count + hi_session_count
    threshold_percentage = (threshold_session_count / total_intensity_sessions) * 100 if total_intensity_sessions > 0 else 0

    # Threshold should dominate (at least 50% of intensity sessions)
    assert threshold_percentage >= 50.0, f"Pyramidal should have ≥50% threshold sessions among intensity work, got {threshold_percentage:.1f}%"


def test_weekly_volume_matches_profile(methodology, validator, valid_user_12_week):
    """Test that weekly volume matches user profile target."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    target_volume = valid_user_12_week.current_state.weekly_volume_hours

    # Check LOAD weeks only (not taper or recovery weeks which have reduced volume)
    load_weeks = [
        w for w in plan.weeks
        if w.phase != TrainingPhase.TAPER and w.week_type == WeekType.LOAD
    ]

    for week in load_weeks:
        # Should be within 20% of target (allows for phase adjustments)
        assert week.total_volume_hours >= target_volume * 0.8
        assert week.total_volume_hours <= target_volume * 1.2


def test_taper_reduces_volume(methodology, validator, valid_user_12_week):
    """Test that taper phase reduces volume appropriately."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    taper_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.TAPER]

    if not taper_weeks:
        pytest.skip("No taper weeks in this plan")

    base_volume = valid_user_12_week.current_state.weekly_volume_hours

    for week in taper_weeks:
        # Taper weeks should be 40-70% of base volume
        assert week.total_volume_hours <= base_volume * 0.7


def test_user_preferences_respected(methodology, validator, valid_user_12_week):
    """Test that user preferences (rest day, long workout day) are respected."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    rest_day = valid_user_12_week.preferences.rest_day
    long_workout_day = valid_user_12_week.preferences.long_workout_day

    for week in plan.weeks:
        session_days = [s.day for s in week.sessions]

        # Rest day should not have sessions
        if rest_day:
            assert rest_day not in session_days

        # Long workout day should have a session (if it's an available day)
        # For this check, we need to derive the list of available days
        from src.plan_schemas import Weekday
        num_training_days = valid_user_12_week.constraints.available_training_days
        all_days = [
            Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY,
            Weekday.FRIDAY, Weekday.SATURDAY, Weekday.SUNDAY,
        ]
        available_days = [day for day in all_days if day != rest_day][:num_training_days]

        if long_workout_day and long_workout_day in available_days:
            # Most weeks should use the long workout day
            # (Allow some flexibility for short plans)
            if week.phase != TrainingPhase.TAPER:
                assert long_workout_day in session_days


def test_all_sessions_have_required_fields(methodology, validator, valid_user_12_week):
    """Test that all sessions have valid required fields."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    for week in plan.weeks:
        for session in week.sessions:
            # Check all required fields are present and valid
            assert session.day is not None
            assert session.session_type is not None
            assert session.primary_zone is not None
            assert session.duration_minutes > 0
            assert len(session.description) >= 10


def test_no_duplicate_days_in_week(methodology, validator, valid_user_12_week):
    """Test that no week has multiple sessions on the same day."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    for week in plan.weeks:
        session_days = [s.day for s in week.sessions]
        # No duplicates
        assert len(session_days) == len(set(session_days))


def test_sessions_respect_available_days(methodology, validator, valid_user_12_week):
    """Test that sessions are only scheduled on available days."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Derive available days from count and rest day
    from src.plan_schemas import Weekday
    num_training_days = valid_user_12_week.constraints.available_training_days
    rest_day = valid_user_12_week.preferences.rest_day

    all_days = [
        Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY,
        Weekday.FRIDAY, Weekday.SATURDAY, Weekday.SUNDAY,
    ]
    available_days = [day for day in all_days if day != rest_day][:num_training_days]

    for week in plan.weeks:
        for session in week.sessions:
            assert session.day in available_days


def test_plan_includes_fragility_score(methodology, validator, valid_user_12_week):
    """Test that plan includes calculated fragility score."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    assert plan.fragility_score is not None
    assert 0.0 <= plan.fragility_score <= 1.0


def test_plan_includes_intensity_distribution(methodology, validator, valid_user_12_week):
    """Test that plan includes intensity distribution summary."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    assert plan.intensity_distribution is not None
    assert plan.intensity_distribution.low_intensity_percent >= 0
    assert plan.intensity_distribution.high_intensity_percent >= 0
    assert plan.intensity_distribution.threshold_percent >= 0


def test_plan_includes_decisions(methodology, validator, valid_user_12_week):
    """Test that plan documents key decisions."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Should have at least 2 decisions:
    # 1. Training Phase Distribution
    # 2. High-Intensity Session Frequency
    assert len(plan.plan_decisions) >= 2

    decision_points = [d.decision_point for d in plan.plan_decisions]
    assert "Training Phase Distribution" in decision_points
    assert "High-Intensity Session Frequency" in decision_points


def test_plan_includes_assumptions(methodology, validator, valid_user_12_week):
    """Test that plan stores assumptions used."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Assumptions should be the user profile dump
    assert plan.assumptions_used is not None
    assert "athlete_id" in plan.assumptions_used
    assert "current_state" in plan.assumptions_used


def test_plan_includes_race_metadata(methodology, validator, valid_user_12_week):
    """Test that plan includes race date and distance."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    assert plan.race_date is not None
    assert plan.race_distance is not None
    assert plan.race_distance == "olympic"


def test_plan_start_date_is_today(methodology, validator, valid_user_12_week):
    """Test that plan start date is set to today."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    assert plan.plan_start_date == date.today()


def test_average_weekly_volume(methodology, validator, valid_user_12_week):
    """Test average weekly volume calculation."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    avg_volume = plan.get_average_weekly_volume()

    # Should be close to target volume (accounting for taper)
    target_volume = valid_user_12_week.current_state.weekly_volume_hours
    assert avg_volume >= target_volume * 0.7  # Taper brings average down
    assert avg_volume <= target_volume * 1.2


def test_week_intensity_distribution_method(methodology, validator, valid_user_12_week):
    """Test that individual weeks can calculate their intensity distribution."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Check a build week
    build_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.BUILD]

    if build_weeks:
        week = build_weeks[0]
        dist = week.get_intensity_distribution()

        # Should have all three categories
        assert "low_intensity" in dist
        assert "threshold" in dist
        assert "high_intensity" in dist

        # Should sum to 100%
        total = dist["low_intensity"] + dist["threshold"] + dist["high_intensity"]
        assert 99.0 <= total <= 101.0


def test_plan_creation_timestamp(methodology, validator, valid_user_12_week):
    """Test that plan includes creation timestamp."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    assert plan.created_at is not None
    # Should be recent (within last minute)
    from datetime import datetime, timedelta

    assert plan.created_at >= datetime.utcnow() - timedelta(minutes=1)


def test_methodology_without_configs_fails():
    """Test that methodologies missing required configs fail validation (breaking change)."""
    from pydantic import ValidationError

    # Create a methodology JSON without required config sections
    incomplete_methodology = {
        "id": "test_incomplete",
        "name": "Incomplete Methodology",
        "version": "1.0.0",
        "last_updated": "2026-01-20",
        "philosophy": {
            "one_line_description": "Test methodology without configs",
            "core_logic": "This should fail validation",
            "metabolic_focus": ["aerobic_base"]
        },
        "assumptions": [
            {
                "key": "sleep_hours",
                "expectation": "≥7.0 hours",
                "reasoning_justification": "Test assumption",
                "criticality": "high",
                "validation_rule": "user.sleep_hours >= 7.0"
            }
        ],
        "safety_gates": {
            "exclusion_criteria": [],
            "refusal_bridge_template": "Test template"
        },
        "risk_profile": {
            "fragility_score": 0.5,
            "sensitivity_factors": ["sleep_consistency"],
            "fragility_calculation_weights": {
                "sleep_deviation": 0.2,
                "stress_multiplier": 0.2,
                "volume_variance": 0.2,
                "intensity_frequency": 0.2,
                "recovery_quality": 0.2
            }
        },
        "failure_modes": [],
        "references": []
        # MISSING: intensity_distribution_config
        # MISSING: session_type_config
        # MISSING: phase_distribution_config
    }

    # This should raise ValidationError due to missing required fields
    with pytest.raises(ValidationError) as exc_info:
        MethodologyModelCard(**incomplete_methodology)

    # Verify the error mentions the missing fields
    error_message = str(exc_info.value)
    assert "intensity_distribution_config" in error_message or \
           "session_type_config" in error_message or \
           "phase_distribution_config" in error_message, \
           "ValidationError should mention missing config fields"


# ============================================================================
# PERIODIZATION / MESOCYCLE TESTS
# ============================================================================


def test_mesocycle_structure_12_week(methodology, validator, valid_user_12_week):
    """Test that 12-week plan has proper mesocycle structure with recovery weeks."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Check that recovery weeks exist in the plan (excluding taper)
    non_taper_weeks = [w for w in plan.weeks if w.phase != TrainingPhase.TAPER]
    recovery_weeks = [w for w in non_taper_weeks if w.week_type == WeekType.RECOVERY]
    load_weeks = [w for w in non_taper_weeks if w.week_type == WeekType.LOAD]

    # With 3:1 ratio and ~10 non-taper weeks, should have 2-3 recovery weeks
    assert len(recovery_weeks) >= 1, "Should have at least 1 recovery week"
    assert len(load_weeks) >= len(recovery_weeks) * 2, "Load weeks should outnumber recovery weeks"


def test_recovery_week_has_reduced_volume(methodology, validator, valid_user_12_week):
    """Test that recovery weeks have appropriately reduced volume (50-60%)."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    target_volume = valid_user_12_week.current_state.weekly_volume_hours

    # Find recovery weeks
    recovery_weeks = [w for w in plan.weeks if w.week_type == WeekType.RECOVERY]

    for week in recovery_weeks:
        # Recovery volume should be 50-60% of target
        assert week.total_volume_hours >= target_volume * 0.45, \
            f"Recovery week {week.week_number} volume too low"
        assert week.total_volume_hours <= target_volume * 0.65, \
            f"Recovery week {week.week_number} volume too high for recovery"
        # Volume multiplier should be set correctly
        assert week.volume_multiplier >= 0.45
        assert week.volume_multiplier <= 0.65


def test_recovery_week_has_limited_hi_sessions(methodology, validator, valid_user_12_week):
    """Test that recovery weeks have at most 1 HI session."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Find recovery weeks
    recovery_weeks = [w for w in plan.weeks if w.week_type == WeekType.RECOVERY]

    for week in recovery_weeks:
        hi_sessions = [
            s for s in week.sessions
            if s.primary_zone in HIGH_INTENSITY_ZONES
        ]
        # Polarized methodology allows max 1 HI session in recovery
        assert len(hi_sessions) <= 1, \
            f"Recovery week {week.week_number} has too many HI sessions ({len(hi_sessions)})"


def test_recovery_week_has_notes(methodology, validator, valid_user_12_week):
    """Test that recovery weeks have contextual notes."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    recovery_weeks = [w for w in plan.weeks if w.week_type == WeekType.RECOVERY]

    for week in recovery_weeks:
        assert week.week_notes is not None, \
            f"Recovery week {week.week_number} should have notes"
        assert "RECOVERY" in week.week_notes.upper(), \
            "Recovery week notes should mention recovery"


def test_mesocycle_metadata_populated(methodology, validator, valid_user_12_week):
    """Test that mesocycle metadata is populated on non-taper weeks."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Non-taper weeks should have mesocycle metadata
    non_taper_weeks = [w for w in plan.weeks if w.phase != TrainingPhase.TAPER]

    for week in non_taper_weeks:
        assert week.mesocycle_number is not None, \
            f"Week {week.week_number} should have mesocycle_number"
        assert week.mesocycle_week is not None, \
            f"Week {week.week_number} should have mesocycle_week"
        assert week.mesocycle_week >= 1
        assert week.mesocycle_week <= 4  # Max for 3:1 ratio


def test_taper_weeks_not_in_mesocycle(methodology, validator, valid_user_12_week):
    """Test that taper weeks are excluded from mesocycle structure."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    taper_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.TAPER]

    for week in taper_weeks:
        assert week.mesocycle_number is None, \
            "Taper weeks should not be part of a mesocycle"
        # Taper weeks are marked as LOAD (they handle their own volume reduction)
        assert week.week_type == WeekType.LOAD


def test_high_fragility_uses_2_1_ratio(methodology, validator, high_fragility_user):
    """Test that high fragility athletes get 2:1 load:recovery ratio."""
    validation_result = validator.validate(high_fragility_user)

    if not validation_result.approved:
        pytest.skip("High fragility user was refused validation")

    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(high_fragility_user)

    # With 2:1 ratio (3-week mesocycles), recovery weeks should be more frequent
    non_taper_weeks = [w for w in plan.weeks if w.phase != TrainingPhase.TAPER]
    recovery_weeks = [w for w in non_taper_weeks if w.week_type == WeekType.RECOVERY]

    # Check plan decisions for ratio selection
    ratio_decisions = [
        d for d in plan.plan_decisions
        if "Load:Recovery Ratio" in d.decision_point
    ]
    assert len(ratio_decisions) >= 1, "Should have ratio selection decision"
    assert "2:1" in ratio_decisions[0].outcome, \
        "High fragility should use 2:1 ratio"


def test_plan_decisions_include_mesocycle_structure(methodology, validator, valid_user_12_week):
    """Test that plan decisions document mesocycle structure."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    decision_points = [d.decision_point for d in plan.plan_decisions]

    assert "Load:Recovery Ratio Selection" in decision_points, \
        "Should document ratio selection"
    assert "Mesocycle Structure" in decision_points, \
        "Should document mesocycle structure"


def test_threshold_methodology_stricter_recovery():
    """Test that Threshold methodology has stricter recovery (0 HI sessions)."""
    # Load Threshold methodology
    methodology_path = Path("models/methodology_threshold_70_20_10_v1.json")
    with open(methodology_path) as f:
        data = json.load(f)
    threshold_methodology = MethodologyModelCard(**data)

    # Load threshold user fixture
    profile_path = Path("tests/fixtures/test_user_threshold_12_week.json")
    with open(profile_path) as f:
        user_data = json.load(f)
    threshold_user = UserProfile(**user_data)

    # Validate and generate plan
    validator = MethodologyValidator(threshold_methodology)
    validation_result = validator.validate(threshold_user)
    assert validation_result.approved, "Threshold user should pass validation"

    generator = TrainingPlanGenerator(threshold_methodology, validation_result)
    plan = generator.generate(threshold_user)

    # Recovery weeks in Threshold methodology should have 0 HI sessions
    recovery_weeks = [w for w in plan.weeks if w.week_type == WeekType.RECOVERY]

    for week in recovery_weeks:
        hi_sessions = [
            s for s in week.sessions
            if s.primary_zone in HIGH_INTENSITY_ZONES
        ]
        assert len(hi_sessions) == 0, \
            f"Threshold recovery week {week.week_number} should have 0 HI sessions"
