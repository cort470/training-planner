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

from src.plan_schemas import IntensityZone, TrainingPhase
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
            if s.primary_zone in [IntensityZone.ZONE_4, IntensityZone.ZONE_5]
        ]

        # High fragility should have 1-2 HI sessions max
        assert len(hi_sessions) <= 2


def test_fragility_normal_hi_frequency_low(methodology, validator, valid_user_12_week):
    """Test that low fragility allows normal HI session frequency."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    # Low-moderate fragility should have 2-3 HI sessions/week
    # Check a build phase week
    build_weeks = [w for w in plan.weeks if w.phase == TrainingPhase.BUILD]

    if build_weeks:
        build_week = build_weeks[0]
        hi_sessions = [
            s
            for s in build_week.sessions
            if s.primary_zone in [IntensityZone.ZONE_4, IntensityZone.ZONE_5]
        ]

        # Low fragility should have 2-3 HI sessions
        assert len(hi_sessions) >= 2


def test_weekly_volume_matches_profile(methodology, validator, valid_user_12_week):
    """Test that weekly volume matches user profile target."""
    validation_result = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, validation_result)
    plan = generator.generate(valid_user_12_week)

    target_volume = valid_user_12_week.current_state.weekly_volume_hours

    # Check base/build phase weeks (not taper)
    non_taper_weeks = [w for w in plan.weeks if w.phase != TrainingPhase.TAPER]

    for week in non_taper_weeks:
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
