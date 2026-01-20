"""
Tests for fragility score calculation.

Ensures that fragility scores are correctly calculated based on
user profile deviations from optimal conditions.
"""

import json
from pathlib import Path

import pytest

from src.fragility import FragilityCalculator, FragilityResult
from src.schemas import UserProfile, StressLevel, HRVTrend, MethodologyModelCard
from src.validator import MethodologyValidator


# Fixtures

@pytest.fixture
def methodology():
    """Load the polarized methodology for testing."""
    methodology_path = Path("models/methodology_polarized.json")
    with open(methodology_path) as f:
        data = json.load(f)
    return MethodologyModelCard(**data)


@pytest.fixture
def fragility_calculator(methodology):
    """Create calculator instance."""
    return FragilityCalculator(methodology)


@pytest.fixture
def valid_user():
    """Load valid user profile (low fragility)."""
    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


# Test Cases


def test_fragility_calculator_initialization(fragility_calculator, methodology):
    """Test that calculator initializes correctly."""
    assert fragility_calculator.methodology == methodology
    assert fragility_calculator.base_fragility == methodology.risk_profile.fragility_score
    assert fragility_calculator.weights == methodology.risk_profile.fragility_calculation_weights


def test_ideal_user_low_fragility(fragility_calculator, valid_user):
    """
    Test that user with ideal conditions has low fragility close to base.

    Valid user has:
    - Sleep: 8.0 hrs (ideal)
    - Stress: low
    - Volume: 10 hrs (within range)
    - Consistency: 8 weeks (good)
    - HRV: stable
    - No recent illness
    """
    result = fragility_calculator.calculate(valid_user)

    # Should be low risk
    assert result.score >= 0.0
    assert result.score <= 1.0
    assert result.interpretation in ["Low Risk", "Moderate Risk"]

    # Should be close to base fragility (minimal penalties)
    base_fragility = fragility_calculator.base_fragility
    assert result.score <= base_fragility + 0.3  # Allow some small penalties

    # Should have all factors in breakdown
    assert "sleep_deviation" in result.breakdown
    assert "stress_multiplier" in result.breakdown
    assert "volume_variance" in result.breakdown
    assert "intensity_frequency" in result.breakdown
    assert "recovery_quality" in result.breakdown

    # Should have recommendations
    assert isinstance(result.recommendations, list)


def test_sleep_deviation_increases_fragility(fragility_calculator, valid_user):
    """Test that reduced sleep increases fragility score."""
    # Baseline with ideal sleep
    baseline_result = fragility_calculator.calculate(valid_user)
    baseline_score = baseline_result.score

    # Modify sleep to 6.5 hours
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.sleep_hours = 6.5

    modified_result = fragility_calculator.calculate(modified_user)
    modified_score = modified_result.score

    # Score should increase
    assert modified_score > baseline_score

    # Sleep deviation contribution should be positive
    assert modified_result.breakdown["sleep_deviation"] > 0.0

    # Should have sleep recommendation
    sleep_recommendations = [
        r for r in modified_result.recommendations if "sleep" in r.lower()
    ]
    assert len(sleep_recommendations) > 0


def test_critically_low_sleep_exponential_penalty(fragility_calculator, valid_user):
    """Test that sleep < 7.0 hours triggers exponential penalty."""
    # Baseline with ideal sleep
    baseline_result = fragility_calculator.calculate(valid_user)

    # Moderate reduction (7.5 hrs)
    moderate_user = valid_user.model_copy(deep=True)
    moderate_user.current_state.sleep_hours = 7.5
    moderate_result = fragility_calculator.calculate(moderate_user)

    # Critical reduction (6.0 hrs - below threshold)
    critical_user = valid_user.model_copy(deep=True)
    critical_user.current_state.sleep_hours = 6.0
    critical_result = fragility_calculator.calculate(critical_user)

    # Critical reduction should have much higher penalty than moderate
    moderate_penalty = moderate_result.breakdown["sleep_deviation"]
    critical_penalty = critical_result.breakdown["sleep_deviation"]

    assert critical_penalty > moderate_penalty


def test_high_stress_increases_fragility(fragility_calculator, valid_user):
    """Test that high stress level increases fragility."""
    # Baseline with low stress
    baseline_result = fragility_calculator.calculate(valid_user)

    # Modify to high stress
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.stress_level = StressLevel.HIGH

    modified_result = fragility_calculator.calculate(modified_user)

    # Score should increase
    assert modified_result.score > baseline_result.score

    # Stress contribution should be positive
    assert modified_result.breakdown["stress_multiplier"] > 0.0

    # Should have stress recommendation
    stress_recommendations = [
        r for r in modified_result.recommendations if "stress" in r.lower()
    ]
    assert len(stress_recommendations) > 0


def test_moderate_stress_penalty(fragility_calculator, valid_user):
    """Test that moderate stress has intermediate penalty."""
    # Low stress
    low_stress_user = valid_user.model_copy(deep=True)
    low_stress_user.current_state.stress_level = StressLevel.LOW
    low_result = fragility_calculator.calculate(low_stress_user)

    # Moderate stress
    moderate_stress_user = valid_user.model_copy(deep=True)
    moderate_stress_user.current_state.stress_level = StressLevel.MODERATE
    moderate_result = fragility_calculator.calculate(moderate_stress_user)

    # High stress
    high_stress_user = valid_user.model_copy(deep=True)
    high_stress_user.current_state.stress_level = StressLevel.HIGH
    high_result = fragility_calculator.calculate(high_stress_user)

    # Penalties should increase in order
    low_penalty = low_result.breakdown["stress_multiplier"]
    moderate_penalty = moderate_result.breakdown["stress_multiplier"]
    high_penalty = high_result.breakdown["stress_multiplier"]

    assert low_penalty < moderate_penalty < high_penalty


def test_volume_too_low_penalty(fragility_calculator, valid_user):
    """Test that volume below 6 hours triggers penalty."""
    # Modify volume to below minimum
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.weekly_volume_hours = 4.0

    result = fragility_calculator.calculate(modified_user)

    # Should have volume variance penalty
    assert result.breakdown["volume_variance"] > 0.0

    # Should have volume recommendation
    volume_recommendations = [
        r for r in result.recommendations if "volume" in r.lower()
    ]
    assert len(volume_recommendations) > 0


def test_volume_too_high_penalty(fragility_calculator, valid_user):
    """Test that volume above 20 hours triggers penalty."""
    # Modify volume to above maximum
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.weekly_volume_hours = 25.0

    result = fragility_calculator.calculate(modified_user)

    # Should have volume variance penalty
    assert result.breakdown["volume_variance"] > 0.0


def test_volume_within_range_no_penalty(fragility_calculator, valid_user):
    """Test that volume within 6-20 hours has minimal penalty."""
    # Test multiple valid volumes
    for volume in [6.0, 10.0, 15.0, 20.0]:
        modified_user = valid_user.model_copy(deep=True)
        modified_user.current_state.weekly_volume_hours = volume
        modified_user.current_state.volume_consistency_weeks = 4  # Ensure consistency

        result = fragility_calculator.calculate(modified_user)

        # Volume variance penalty should be very low or zero
        assert result.breakdown["volume_variance"] <= 0.05  # Allow minimal penalty


def test_volume_consistency_penalty(fragility_calculator, valid_user):
    """Test that insufficient consistency weeks triggers penalty."""
    # Modify consistency to below minimum
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.volume_consistency_weeks = 2

    result = fragility_calculator.calculate(modified_user)

    # Should have volume variance penalty
    assert result.breakdown["volume_variance"] > 0.0


def test_short_race_timeline_penalty(fragility_calculator, valid_user):
    """Test that short timeline to race increases intensity penalty."""
    # Modify to short timeline (4 weeks)
    modified_user = valid_user.model_copy(deep=True)
    modified_user.goals.weeks_to_race = 4

    result = fragility_calculator.calculate(modified_user)

    # Should have significant intensity frequency contribution
    # (penalty is high ~0.8, but weighted by 0.08, so contribution ~0.064)
    assert result.breakdown["intensity_frequency"] > 0.05


def test_long_race_timeline_low_penalty(fragility_calculator, valid_user):
    """Test that long timeline to race has low intensity penalty."""
    # Modify to long timeline (24 weeks)
    modified_user = valid_user.model_copy(deep=True)
    modified_user.goals.weeks_to_race = 24

    result = fragility_calculator.calculate(modified_user)

    # Should have low intensity frequency penalty
    assert result.breakdown["intensity_frequency"] < 0.3


def test_decreasing_hrv_recovery_penalty(fragility_calculator, valid_user):
    """Test that decreasing HRV trend increases recovery penalty."""
    # Modify HRV to decreasing
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.hrv_trend = HRVTrend.DECREASING

    result = fragility_calculator.calculate(modified_user)

    # Should have significant recovery quality contribution
    # (penalty is high ~0.7, but weighted by 0.10, so contribution ~0.07)
    assert result.breakdown["recovery_quality"] > 0.05

    # Should have HRV recommendation
    hrv_recommendations = [
        r for r in result.recommendations if "hrv" in r.lower()
    ]
    assert len(hrv_recommendations) > 0


def test_increasing_hrv_low_penalty(fragility_calculator, valid_user):
    """Test that increasing HRV trend has low recovery penalty."""
    # Modify HRV to increasing
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.hrv_trend = HRVTrend.INCREASING

    result = fragility_calculator.calculate(modified_user)

    # Should have low recovery quality penalty
    assert result.breakdown["recovery_quality"] < 0.3


def test_recent_illness_penalty(fragility_calculator, valid_user):
    """Test that recent illness increases recovery penalty."""
    # Modify to recent illness
    modified_user = valid_user.model_copy(deep=True)
    modified_user.current_state.recent_illness = True

    result = fragility_calculator.calculate(modified_user)

    # Should have increased recovery quality penalty
    assert result.breakdown["recovery_quality"] > 0.0

    # Should have illness recommendation
    illness_recommendations = [
        r for r in result.recommendations if "illness" in r.lower()
    ]
    assert len(illness_recommendations) > 0


def test_compound_factors_increase_fragility(fragility_calculator, valid_user):
    """Test that multiple negative factors compound to high fragility."""
    # Create high fragility user
    high_fragility_user = valid_user.model_copy(deep=True)
    high_fragility_user.current_state.sleep_hours = 6.0
    high_fragility_user.current_state.stress_level = StressLevel.HIGH
    high_fragility_user.current_state.weekly_volume_hours = 25.0
    high_fragility_user.current_state.hrv_trend = HRVTrend.DECREASING
    high_fragility_user.current_state.recent_illness = True
    high_fragility_user.goals.weeks_to_race = 4

    result = fragility_calculator.calculate(high_fragility_user)

    # Should have high or critical risk
    assert result.interpretation in ["High Risk", "Critical Risk"]
    assert result.score >= 0.6

    # Should have multiple recommendations
    assert len(result.recommendations) >= 3


def test_fragility_score_clamped_to_range(fragility_calculator, valid_user):
    """Test that fragility score never exceeds 1.0."""
    # Create extreme negative conditions
    extreme_user = valid_user.model_copy(deep=True)
    extreme_user.current_state.sleep_hours = 4.0
    extreme_user.current_state.stress_level = StressLevel.HIGH
    extreme_user.current_state.weekly_volume_hours = 30.0
    extreme_user.current_state.volume_consistency_weeks = 1
    extreme_user.current_state.hrv_trend = HRVTrend.DECREASING
    extreme_user.current_state.recent_illness = True
    extreme_user.goals.weeks_to_race = 2

    result = fragility_calculator.calculate(extreme_user)

    # Score must be within valid range
    assert 0.0 <= result.score <= 1.0


def test_interpretation_thresholds(fragility_calculator, methodology):
    """Test that interpretation thresholds are correct."""
    # Low Risk: < 0.4
    low_result = FragilityResult(
        score=0.3,
        breakdown={},
        interpretation=fragility_calculator._interpret_score(0.3),
        recommendations=[],
    )
    assert low_result.interpretation == "Low Risk"

    # Moderate Risk: 0.4 - 0.6
    moderate_result = FragilityResult(
        score=0.5,
        breakdown={},
        interpretation=fragility_calculator._interpret_score(0.5),
        recommendations=[],
    )
    assert moderate_result.interpretation == "Moderate Risk"

    # High Risk: 0.6 - 0.8
    high_result = FragilityResult(
        score=0.7,
        breakdown={},
        interpretation=fragility_calculator._interpret_score(0.7),
        recommendations=[],
    )
    assert high_result.interpretation == "High Risk"

    # Critical Risk: >= 0.8
    critical_result = FragilityResult(
        score=0.9,
        breakdown={},
        interpretation=fragility_calculator._interpret_score(0.9),
        recommendations=[],
    )
    assert critical_result.interpretation == "Critical Risk"


def test_fragility_result_schema_validation():
    """Test that FragilityResult schema validates correctly."""
    # Valid result
    result = FragilityResult(
        score=0.5,
        breakdown={
            "sleep_deviation": 0.028,
            "stress_multiplier": 0.036,
            "volume_variance": 0.0,
            "intensity_frequency": 0.032,
            "recovery_quality": 0.030,
        },
        interpretation="Moderate Risk",
        recommendations=["Increase sleep to reduce fragility"],
    )

    assert result.score == 0.5
    assert len(result.breakdown) == 5
    assert result.interpretation == "Moderate Risk"
    assert len(result.recommendations) == 1

    # Invalid score (out of range)
    with pytest.raises(Exception):  # Pydantic ValidationError
        FragilityResult(
            score=1.5,  # Invalid
            breakdown={},
            interpretation="Invalid",
            recommendations=[],
        )


def test_hrv_amplifies_intensity_penalty(fragility_calculator, valid_user):
    """Test that decreasing HRV amplifies intensity frequency penalty."""
    # Short timeline with increasing HRV
    increasing_hrv_user = valid_user.model_copy(deep=True)
    increasing_hrv_user.goals.weeks_to_race = 4
    increasing_hrv_user.current_state.hrv_trend = HRVTrend.INCREASING
    increasing_result = fragility_calculator.calculate(increasing_hrv_user)

    # Short timeline with decreasing HRV
    decreasing_hrv_user = valid_user.model_copy(deep=True)
    decreasing_hrv_user.goals.weeks_to_race = 4
    decreasing_hrv_user.current_state.hrv_trend = HRVTrend.DECREASING
    decreasing_result = fragility_calculator.calculate(decreasing_hrv_user)

    # Decreasing HRV should amplify intensity penalty
    increasing_penalty = increasing_result.breakdown["intensity_frequency"]
    decreasing_penalty = decreasing_result.breakdown["intensity_frequency"]

    assert decreasing_penalty > increasing_penalty
