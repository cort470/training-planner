"""
Tests for Pydantic schema validation.

Ensures that schemas properly validate data and enforce constraints.
"""

import json
from pathlib import Path
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.schemas import (
    MethodologyModelCard,
    UserProfile,
    CurrentState,
    Goals,
    StressLevel,
    PrimaryGoal,
    RaceDistance,
    Severity,
    Criticality,
    ReasoningTrace,
    AssumptionCheck,
    GateViolation,
)


# Methodology Schema Tests

def test_methodology_loads_from_file():
    """Test that methodology JSON can be loaded and validated."""
    methodology_path = Path("models/methodology_polarized.json")
    with open(methodology_path) as f:
        data = json.load(f)

    methodology = MethodologyModelCard(**data)

    assert methodology.id == "polarized_80_20_v1"
    assert methodology.name == "Polarized 80/20 Training"
    assert methodology.version == "1.0.0"


def test_methodology_requires_id():
    """Test that methodology requires an ID."""
    with pytest.raises(ValidationError):
        MethodologyModelCard(
            # id missing
            name="Test Methodology",
            version="1.0.0",
            last_updated=date.today(),
            philosophy={
                "one_line_description": "Test",
                "core_logic": "Test logic",
            },
            assumptions=[],
            safety_gates={"exclusion_criteria": [], "refusal_bridge_template": ""},
            risk_profile={"fragility_score": 0.5, "sensitivity_factors": []},
        )


def test_methodology_id_format():
    """Test that methodology ID must be snake_case."""
    with pytest.raises(ValidationError):
        MethodologyModelCard(
            id="Invalid-ID-Format",  # Should be snake_case
            name="Test",
            version="1.0.0",
            last_updated=date.today(),
            philosophy={
                "one_line_description": "Test",
                "core_logic": "Test logic",
            },
            assumptions=[
                {
                    "key": "test",
                    "expectation": "test",
                    "reasoning_justification": "test",
                    "validation_rule": "test",
                }
            ],
            safety_gates={
                "exclusion_criteria": [
                    {
                        "condition": "test",
                        "threshold": "test",
                        "severity": "blocking",
                        "validation_logic": "test",
                        "bridge_action": "test",
                    }
                ],
                "refusal_bridge_template": "test",
            },
            risk_profile={"fragility_score": 0.5, "sensitivity_factors": []},
        )


def test_fragility_score_range():
    """Test that fragility score must be between 0 and 1."""
    methodology_path = Path("models/methodology_polarized.json")
    with open(methodology_path) as f:
        data = json.load(f)

    # Valid score
    data["risk_profile"]["fragility_score"] = 0.5
    methodology = MethodologyModelCard(**data)
    assert methodology.risk_profile.fragility_score == 0.5

    # Invalid score (too high)
    data["risk_profile"]["fragility_score"] = 1.5
    with pytest.raises(ValidationError):
        MethodologyModelCard(**data)

    # Invalid score (negative)
    data["risk_profile"]["fragility_score"] = -0.1
    with pytest.raises(ValidationError):
        MethodologyModelCard(**data)


def test_severity_enum():
    """Test that severity must be valid enum value."""
    assert Severity.BLOCKING.value == "blocking"
    assert Severity.WARNING.value == "warning"

    # Only two valid values
    with pytest.raises(ValueError):
        Severity("critical")


def test_criticality_enum():
    """Test that criticality must be valid enum value."""
    assert Criticality.LOW.value == "low"
    assert Criticality.MEDIUM.value == "medium"
    assert Criticality.HIGH.value == "high"


# User Profile Schema Tests

def test_user_profile_loads_from_file():
    """Test that user profile JSON can be loaded and validated."""
    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        data = json.load(f)

    profile = UserProfile(**data)

    assert profile.athlete_id == "test_athlete_001"
    assert profile.current_state.sleep_hours == 8.0
    assert profile.current_state.injury_status is False


def test_user_profile_requires_athlete_id():
    """Test that user profile requires athlete_id."""
    with pytest.raises(ValidationError):
        UserProfile(
            # athlete_id missing
            profile_date=date.today(),
            current_state=CurrentState(
                sleep_hours=7.5,
                injury_status=False,
                stress_level=StressLevel.LOW,
                weekly_volume_hours=10.0,
            ),
            goals=Goals(primary_goal=PrimaryGoal.RACE_PERFORMANCE),
        )


def test_sleep_hours_range():
    """Test that sleep_hours must be in valid range (4-12)."""
    # Valid
    state = CurrentState(
        sleep_hours=7.5,
        injury_status=False,
        stress_level=StressLevel.LOW,
        weekly_volume_hours=10.0,
    )
    assert state.sleep_hours == 7.5

    # Too low
    with pytest.raises(ValidationError):
        CurrentState(
            sleep_hours=3.0,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=10.0,
        )

    # Too high
    with pytest.raises(ValidationError):
        CurrentState(
            sleep_hours=13.0,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=10.0,
        )


def test_stress_level_enum():
    """Test that stress_level must be valid enum."""
    assert StressLevel.LOW.value == "low"
    assert StressLevel.MODERATE.value == "moderate"
    assert StressLevel.HIGH.value == "high"

    # Only three valid values
    with pytest.raises(ValueError):
        StressLevel("extreme")


def test_weekly_volume_range():
    """Test that weekly_volume_hours must be in valid range (0-40)."""
    # Valid
    state = CurrentState(
        sleep_hours=7.5,
        injury_status=False,
        stress_level=StressLevel.LOW,
        weekly_volume_hours=15.0,
    )
    assert state.weekly_volume_hours == 15.0

    # Negative (invalid)
    with pytest.raises(ValidationError):
        CurrentState(
            sleep_hours=7.5,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=-5.0,
        )

    # Too high
    with pytest.raises(ValidationError):
        CurrentState(
            sleep_hours=7.5,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=50.0,
        )


def test_injury_status_boolean():
    """Test that injury_status is boolean."""
    state = CurrentState(
        sleep_hours=7.5,
        injury_status=True,
        stress_level=StressLevel.LOW,
        weekly_volume_hours=10.0,
    )
    assert state.injury_status is True
    assert isinstance(state.injury_status, bool)


# Reasoning Trace Schema Tests

def test_reasoning_trace_creation():
    """Test creating a reasoning trace."""
    trace = ReasoningTrace(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
        result="approved",
    )

    assert trace.methodology_id == "polarized_80_20_v1"
    assert trace.athlete_id == "test_athlete_001"
    assert trace.result == "approved"
    assert trace.timestamp is not None
    assert len(trace.checks) == 0
    assert len(trace.safety_gates) == 0


def test_assumption_check_creation():
    """Test creating an assumption check."""
    check = AssumptionCheck(
        assumption_key="sleep_hours",
        passed=True,
        user_value=8.0,
        threshold=7.0,
        reasoning="Sleep exceeds minimum requirement",
    )

    assert check.assumption_key == "sleep_hours"
    assert check.passed is True
    assert check.user_value == 8.0
    assert check.threshold == 7.0


def test_gate_violation_creation():
    """Test creating a gate violation."""
    violation = GateViolation(
        condition="injury_status",
        threshold="true",
        severity=Severity.BLOCKING,
        bridge="Seek medical clearance",
    )

    assert violation.condition == "injury_status"
    assert violation.threshold == "true"
    assert violation.severity == Severity.BLOCKING
    assert violation.bridge == "Seek medical clearance"


def test_trace_with_checks_and_violations():
    """Test reasoning trace with checks and violations."""
    trace = ReasoningTrace(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
        result="refused",
    )

    # Add checks
    trace.checks.append(
        AssumptionCheck(
            assumption_key="sleep_hours",
            passed=True,
            user_value=8.0,
            threshold=7.0,
            reasoning="Sleep OK",
        )
    )

    trace.checks.append(
        AssumptionCheck(
            assumption_key="injury_status",
            passed=False,
            user_value=True,
            threshold=False,
            reasoning="Injury present",
        )
    )

    # Add violation
    trace.safety_gates.append(
        GateViolation(
            condition="injury_status",
            threshold="true",
            severity=Severity.BLOCKING,
            bridge="Seek medical clearance",
        )
    )

    assert len(trace.checks) == 2
    assert len(trace.safety_gates) == 1
    assert trace.result == "refused"


def test_fragility_score_in_trace():
    """Test that fragility score can be set in trace."""
    trace = ReasoningTrace(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
        result="approved",
        fragility_score=0.4,
    )

    assert trace.fragility_score == 0.4

    # Score must be in valid range
    with pytest.raises(ValidationError):
        ReasoningTrace(
            methodology_id="polarized_80_20_v1",
            athlete_id="test_athlete_001",
            result="approved",
            fragility_score=1.5,  # Too high
        )


# Edge Cases and Validation

def test_optional_fields():
    """Test that optional fields can be omitted."""
    # Minimal user profile
    profile = UserProfile(
        athlete_id="minimal_user",
        profile_date=date.today(),
        current_state=CurrentState(
            sleep_hours=7.5,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=10.0,
        ),
        goals=Goals(primary_goal=PrimaryGoal.GENERAL_FITNESS),
    )

    assert profile.training_history is None
    assert profile.constraints is None
    assert profile.preferences is None
    assert profile.metadata is None


def test_date_serialization():
    """Test that dates are properly serialized."""
    profile = UserProfile(
        athlete_id="test_user",
        profile_date=date(2026, 1, 19),
        current_state=CurrentState(
            sleep_hours=7.5,
            injury_status=False,
            stress_level=StressLevel.LOW,
            weekly_volume_hours=10.0,
        ),
        goals=Goals(
            primary_goal=PrimaryGoal.RACE_PERFORMANCE,
            race_date=date(2026, 6, 1),
        ),
    )

    # Should serialize to dict
    data = profile.model_dump(mode="json")
    assert data["profile_date"] == "2026-01-19"
    assert data["goals"]["race_date"] == "2026-06-01"


def test_all_fixture_files_valid():
    """Test that all fixture files are valid schemas."""
    fixtures_dir = Path("tests/fixtures")

    for fixture_file in fixtures_dir.glob("test_user_*.json"):
        with open(fixture_file) as f:
            data = json.load(f)

        # Should not raise validation error
        profile = UserProfile(**data)
        assert profile is not None
        assert profile.athlete_id is not None
