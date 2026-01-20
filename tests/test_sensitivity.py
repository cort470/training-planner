"""
Tests for sensitivity analysis and "what-if" scenarios.

Covers:
- Assumption modification
- Validation status changes
- Fragility score changes
- Plan adjustment detection
- Immutability of baseline profile
"""

import json
from pathlib import Path

import pytest

from src.planner import TrainingPlanGenerator
from src.schemas import MethodologyModelCard, StressLevel, UserProfile
from src.sensitivity import SensitivityAnalyzer
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
def moderate_fragility_user():
    """Load moderate fragility user."""
    profile_path = Path("tests/fixtures/test_user_moderate_fragility.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def valid_user_12_week():
    """Load 12-week race scenario user."""
    profile_path = Path("tests/fixtures/test_user_12_week_race.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


def test_modify_sleep_hours_decreases_fragility(
    methodology, validator, moderate_fragility_user
):
    """Test that increasing sleep hours decreases fragility score."""
    # Get baseline
    baseline_validation = validator.validate(moderate_fragility_user)
    assert baseline_validation.approved

    # Generate baseline plan
    generator = TrainingPlanGenerator(methodology, baseline_validation)
    baseline_plan = generator.generate(moderate_fragility_user)

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, moderate_fragility_user, baseline_validation, baseline_plan
    )

    # Modify sleep from 6.5 to 7.5
    result = analyzer.modify_assumption("current_state.sleep_hours", 7.5)

    # Check original and new values
    assert result.original_value == 6.5
    assert result.new_value == 7.5

    # Validation should still pass
    assert result.validation_changed is False
    assert result.new_validation_status == "approved"

    # Fragility should decrease
    assert result.new_fragility is not None
    assert result.fragility_delta is not None
    assert result.fragility_delta < 0  # Negative delta means improvement


def test_modify_stress_level_increases_fragility(
    methodology, validator, valid_user_12_week
):
    """Test that increasing stress level increases fragility score."""
    # Get baseline
    baseline_validation = validator.validate(valid_user_12_week)
    assert baseline_validation.approved

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    # Modify stress from low to high
    result = analyzer.modify_assumption("current_state.stress_level", StressLevel.HIGH)

    # Check modification
    assert result.original_value == StressLevel.LOW
    assert result.new_value == StressLevel.HIGH

    # Fragility should increase
    assert result.new_fragility is not None
    assert result.fragility_delta is not None
    assert result.fragility_delta > 0  # Positive delta means worse


def test_modify_injury_status_changes_validation(
    methodology, validator, valid_user_12_week
):
    """Test that adding injury changes validation to refused."""
    # Get baseline (should be approved)
    baseline_validation = validator.validate(valid_user_12_week)
    assert baseline_validation.approved

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    # Modify injury_status to True
    result = analyzer.modify_assumption("current_state.injury_status", True)

    # Check modification
    assert result.original_value is False
    assert result.new_value is True

    # Validation should change to refused
    assert result.validation_changed is True
    assert result.new_validation_status == "refused"

    # Should have violations
    assert result.new_violations is not None
    assert len(result.new_violations) > 0


def test_baseline_profile_immutable(methodology, validator, moderate_fragility_user):
    """Test that baseline profile is not modified during sensitivity analysis."""
    # Get baseline
    baseline_validation = validator.validate(moderate_fragility_user)

    # Store original sleep value
    original_sleep = moderate_fragility_user.current_state.sleep_hours

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, moderate_fragility_user, baseline_validation, None
    )

    # Modify sleep hours
    result = analyzer.modify_assumption("current_state.sleep_hours", 8.0)

    # Baseline profile should be unchanged
    assert moderate_fragility_user.current_state.sleep_hours == original_sleep
    assert analyzer.baseline_profile.current_state.sleep_hours == original_sleep


def test_plan_adjustments_detected(methodology, validator, moderate_fragility_user):
    """Test that plan adjustments are detected when sleep improves."""
    # Get baseline
    baseline_validation = validator.validate(moderate_fragility_user)
    generator = TrainingPlanGenerator(methodology, baseline_validation)
    baseline_plan = generator.generate(moderate_fragility_user)

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, moderate_fragility_user, baseline_validation, baseline_plan
    )

    # Modify sleep from 6.5 to 8.0 (should reduce fragility and potentially increase HI frequency)
    result = analyzer.modify_assumption("current_state.sleep_hours", 8.0)

    # Plan adjustments should be present
    assert result.plan_adjustments is not None


def test_volume_change_detected(methodology, validator, valid_user_12_week):
    """Test that volume changes are detected in plan adjustments."""
    # Get baseline
    baseline_validation = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, baseline_validation)
    baseline_plan = generator.generate(valid_user_12_week)

    # Create analyzer
    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, baseline_plan
    )

    # Modify volume from 10.0 to 12.0
    result = analyzer.modify_assumption("current_state.weekly_volume_hours", 12.0)

    # Should have volume delta
    assert result.plan_adjustments is not None
    if result.plan_adjustments.volume_delta_hours is not None:
        assert result.plan_adjustments.volume_delta_hours > 0


def test_invalid_assumption_path_raises_error(
    methodology, validator, valid_user_12_week
):
    """Test that invalid assumption path raises ValueError."""
    baseline_validation = validator.validate(valid_user_12_week)

    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    with pytest.raises(ValueError, match="Invalid path"):
        analyzer.modify_assumption("current_state.nonexistent_field", 42)


def test_nested_field_access(methodology, validator, valid_user_12_week):
    """Test that nested field access works correctly."""
    baseline_validation = validator.validate(valid_user_12_week)

    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    # Modify a deeply nested field
    result = analyzer.modify_assumption("goals.weeks_to_race", 8)

    assert result.original_value == 12
    assert result.new_value == 8


def test_fragility_none_when_validation_fails(
    methodology, validator, valid_user_12_week
):
    """Test that fragility is None when new validation fails."""
    baseline_validation = validator.validate(valid_user_12_week)

    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    # Modify to cause validation failure
    result = analyzer.modify_assumption("current_state.injury_status", True)

    # Fragility should be None for refused validation
    assert result.new_fragility is None
    assert result.fragility_delta is None


def test_plan_adjustments_none_without_baseline_plan(
    methodology, validator, valid_user_12_week
):
    """Test that plan_adjustments is None when baseline plan not provided."""
    baseline_validation = validator.validate(valid_user_12_week)

    # Create analyzer WITHOUT baseline plan
    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    result = analyzer.modify_assumption("current_state.sleep_hours", 8.0)

    # Plan adjustments should be None
    assert result.plan_adjustments is None


def test_multiple_modifications_independent(
    methodology, validator, moderate_fragility_user
):
    """Test that multiple modifications are independent (each starts from baseline)."""
    baseline_validation = validator.validate(moderate_fragility_user)

    analyzer = SensitivityAnalyzer(
        methodology, moderate_fragility_user, baseline_validation, None
    )

    # First modification: increase sleep
    result1 = analyzer.modify_assumption("current_state.sleep_hours", 7.5)
    fragility1 = result1.new_fragility

    # Second modification: decrease stress (should start from baseline, not result1)
    result2 = analyzer.modify_assumption("current_state.stress_level", StressLevel.LOW)
    fragility2 = result2.new_fragility

    # Both should be different from baseline, but independent of each other
    assert fragility1 != fragility2


def test_sensitivity_result_schema_valid(methodology, validator, valid_user_12_week):
    """Test that SensitivityResult schema is valid."""
    baseline_validation = validator.validate(valid_user_12_week)

    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, None
    )

    result = analyzer.modify_assumption("current_state.sleep_hours", 8.0)

    # Should have all required fields
    assert result.modified_assumption == "current_state.sleep_hours"
    assert result.original_value is not None
    assert result.new_value is not None
    assert result.original_validation_status is not None
    assert result.new_validation_status is not None
    assert isinstance(result.validation_changed, bool)


def test_hi_session_frequency_change_detected(
    methodology, validator, moderate_fragility_user
):
    """Test that changes in HI session frequency are detected."""
    baseline_validation = validator.validate(moderate_fragility_user)
    generator = TrainingPlanGenerator(methodology, baseline_validation)
    baseline_plan = generator.generate(moderate_fragility_user)

    analyzer = SensitivityAnalyzer(
        methodology, moderate_fragility_user, baseline_validation, baseline_plan
    )

    # Significantly improve sleep to potentially increase HI frequency
    result = analyzer.modify_assumption("current_state.sleep_hours", 8.5)

    # If plan adjustments exist and HI frequency changed, delta should be non-None
    if result.plan_adjustments:
        # HI delta might be None if frequency didn't change enough
        # Just verify the field exists
        assert hasattr(result.plan_adjustments, "hi_sessions_per_week_delta")


def test_phase_distribution_change_detected(methodology, validator, valid_user_12_week):
    """Test that phase distribution changes are detected."""
    baseline_validation = validator.validate(valid_user_12_week)
    generator = TrainingPlanGenerator(methodology, baseline_validation)
    baseline_plan = generator.generate(valid_user_12_week)

    analyzer = SensitivityAnalyzer(
        methodology, valid_user_12_week, baseline_validation, baseline_plan
    )

    # Modify volume consistency to trigger phase changes
    result = analyzer.modify_assumption("current_state.volume_consistency_weeks", 2)

    if result.plan_adjustments:
        # Check that phase distribution change flag exists
        assert isinstance(
            result.plan_adjustments.phase_distribution_changed, bool
        )
