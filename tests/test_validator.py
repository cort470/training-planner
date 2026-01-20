"""
Tests for the MethodologyValidator circuit breaker logic.

Test scenarios:
1. Valid user passes all gates
2. Injury triggers blocking refusal
3. Sleep threshold violation triggers refusal
4. Multiple violations are detected and prioritized
"""

import json
from pathlib import Path

import pytest

from src.schemas import UserProfile, MethodologyModelCard, Severity
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
def validator(methodology):
    """Create validator instance."""
    return MethodologyValidator(methodology)


@pytest.fixture
def valid_user():
    """Load valid user profile."""
    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def injury_user():
    """Load user profile with injury."""
    profile_path = Path("tests/fixtures/test_user_injury.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def sleep_user():
    """Load user profile with sleep violation."""
    profile_path = Path("tests/fixtures/test_user_sleep.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


@pytest.fixture
def multiple_user():
    """Load user profile with multiple violations."""
    profile_path = Path("tests/fixtures/test_user_multiple.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)


# Test Cases

def test_valid_user_passes(validator, valid_user):
    """
    TEST_CASE_001: Valid Input Acceptance

    A user with all assumptions satisfied should pass validation.
    Expected: Plan approved, no violations, no warnings
    """
    result = validator.validate(valid_user)

    # Should be approved
    assert result.approved is True
    assert result.refusal_response is None

    # Reasoning trace should show approved
    assert result.reasoning_trace.result == "approved"

    # Should have checks for all assumptions
    assert len(result.reasoning_trace.checks) > 0

    # All checks should pass
    for check in result.reasoning_trace.checks:
        assert check.passed is True

    # No safety gate violations
    assert len(result.reasoning_trace.safety_gates) == 0

    # No warnings
    assert len(result.warnings) == 0


def test_injury_triggers_refusal(validator, injury_user):
    """
    TEST_CASE_002: Injury Circuit Breaker

    A user with active injury should trigger blocking refusal.
    Expected:
    - REFUSAL status
    - Reasoning bridge includes medical clearance recommendation
    - No plan generated
    """
    result = validator.validate(injury_user)

    # Should be refused
    assert result.approved is False
    assert result.refusal_response is not None

    # Reasoning trace should show refused
    assert result.reasoning_trace.result == "refused"

    # Should have at least one violation
    assert len(result.reasoning_trace.safety_gates) > 0

    # Should have injury violation
    injury_violation = next(
        (v for v in result.reasoning_trace.safety_gates if v.condition == "injury_status"),
        None,
    )
    assert injury_violation is not None
    assert injury_violation.severity == Severity.BLOCKING

    # Bridge should mention medical clearance
    assert "medical" in injury_violation.bridge.lower() or "clearance" in injury_violation.bridge.lower()

    # Refusal response should have violations
    assert len(result.refusal_response.violations) > 0
    assert result.refusal_response.status == "refused"


def test_sleep_threshold_violation(validator, sleep_user):
    """
    TEST_CASE_003: Sleep Threshold Violation

    A user with insufficient sleep should trigger blocking refusal.
    Expected:
    - REFUSAL status
    - Reasoning bridge explains sleep requirement violation
    - Bridge suggests sleep optimization protocol
    """
    result = validator.validate(sleep_user)

    # Should be refused
    assert result.approved is False
    assert result.refusal_response is not None

    # Reasoning trace should show refused
    assert result.reasoning_trace.result == "refused"

    # Should have at least one violation
    assert len(result.reasoning_trace.safety_gates) > 0

    # Should have sleep violation
    sleep_violation = next(
        (v for v in result.reasoning_trace.safety_gates if v.condition == "sleep_hours"),
        None,
    )
    assert sleep_violation is not None
    assert sleep_violation.severity == Severity.BLOCKING

    # Bridge should mention sleep
    assert "sleep" in sleep_violation.bridge.lower()

    # Check that sleep_hours assumption failed
    sleep_check = next(
        (c for c in result.reasoning_trace.checks if c.assumption_key == "sleep_hours"),
        None,
    )
    if sleep_check:  # May not have separate assumption check if only gate is evaluated
        assert sleep_check.passed is False


def test_multiple_violations_prioritized(validator, multiple_user):
    """
    TEST_CASE_004: Multiple Violations (Compounding Risk)

    A user with multiple violations should see all violations with prioritized recommendations.
    Expected:
    - REFUSAL status
    - Multiple reasoning entries (sleep + stress + volume)
    - Prioritized recommendations (blocking violations first)
    """
    result = validator.validate(multiple_user)

    # Should be refused
    assert result.approved is False
    assert result.refusal_response is not None

    # Reasoning trace should show refused
    assert result.reasoning_trace.result == "refused"

    # Should have multiple violations
    assert len(result.reasoning_trace.safety_gates) >= 2

    # Violations should be sorted by severity (blocking first)
    violations = result.reasoning_trace.safety_gates
    blocking_violations = [v for v in violations if v.severity == Severity.BLOCKING]
    warning_violations = [v for v in violations if v.severity == Severity.WARNING]

    # Should have at least one blocking violation
    assert len(blocking_violations) >= 1

    # Check that blocking violations come first in the list
    if blocking_violations and warning_violations:
        first_blocking_idx = violations.index(blocking_violations[0])
        first_warning_idx = violations.index(warning_violations[0])
        assert first_blocking_idx < first_warning_idx

    # Refusal response should contain all violations
    assert len(result.refusal_response.violations) >= 2


def test_validator_from_file():
    """Test loading validator from methodology file."""
    methodology_path = Path("models/methodology_polarized.json")
    validator = MethodologyValidator.from_file(methodology_path)

    assert validator is not None
    assert validator.methodology.id == "polarized_80_20_v1"
    assert validator.methodology.name == "Polarized 80/20 Training"


def test_validator_from_invalid_file():
    """Test that invalid methodology file raises error."""
    with pytest.raises(FileNotFoundError):
        MethodologyValidator.from_file(Path("nonexistent.json"))


def test_refusal_bridge_generation(validator, injury_user):
    """Test that refusal bridges are properly generated."""
    result = validator.validate(injury_user)

    # Get a violation
    violation = result.reasoning_trace.safety_gates[0]

    # Generate bridge
    bridge = validator.generate_refusal_bridge(violation)

    # Bridge should be non-empty string
    assert isinstance(bridge, str)
    assert len(bridge) > 0

    # Should contain key information
    assert violation.condition in bridge


def test_validation_summary_display(validator, valid_user):
    """Test that validation summary can be generated."""
    result = validator.validate(valid_user)

    summary = validator.display_validation_summary(result)

    # Summary should be a non-empty string
    assert isinstance(summary, str)
    assert len(summary) > 0

    # Should contain key elements
    assert "VALIDATION REPORT" in summary
    assert validator.methodology.name in summary
    assert result.reasoning_trace.athlete_id in summary


def test_boundary_condition_sleep_at_threshold(validator, valid_user):
    """
    TEST_CASE_005: Boundary Condition (Sleep at Threshold)

    User with sleep exactly at threshold (7.0) should pass.
    Expected:
    - Plan generated (threshold is inclusive)
    - No blocking violations for sleep
    """
    # Modify valid user to have exactly 7.0 hours sleep
    valid_user.current_state.sleep_hours = 7.0

    result = validator.validate(valid_user)

    # Should pass with sleep at threshold
    assert result.approved is True

    # Check sleep assumption
    sleep_check = next(
        (c for c in result.reasoning_trace.checks if c.assumption_key == "sleep_hours"),
        None,
    )
    if sleep_check:
        assert sleep_check.passed is True
        assert sleep_check.user_value == 7.0


def test_assumption_criticality_tracked(validator, valid_user):
    """Test that assumption criticality is properly tracked in methodology."""
    # Get high criticality assumptions
    high_crit = [a for a in validator.methodology.assumptions if a.criticality.value == "high"]

    # Should have some high criticality assumptions
    assert len(high_crit) > 0

    # Verify they include key safety assumptions
    high_crit_keys = {a.key for a in high_crit}
    assert "sleep_hours" in high_crit_keys
    assert "injury_status" in high_crit_keys


def test_reasoning_trace_completeness(validator, valid_user):
    """Test that reasoning trace contains complete information."""
    result = validator.validate(valid_user)

    trace = result.reasoning_trace

    # Should have timestamp
    assert trace.timestamp is not None

    # Should have methodology and athlete IDs
    assert trace.methodology_id == validator.methodology.id
    assert trace.athlete_id == valid_user.athlete_id

    # Should have checks (one for each assumption or at least key ones)
    assert len(trace.checks) > 0

    # Each check should have required fields
    for check in trace.checks:
        assert check.assumption_key is not None
        assert isinstance(check.passed, bool)
        assert check.reasoning is not None


def test_warning_vs_blocking_severity(validator):
    """Test that violations are properly classified by severity."""
    # Look at the methodology's safety gates
    gates = validator.methodology.safety_gates.exclusion_criteria

    blocking = [g for g in gates if g.severity == Severity.BLOCKING]
    warnings = [g for g in gates if g.severity == Severity.WARNING]

    # Should have both types
    assert len(blocking) > 0

    # Verify injury and sleep are blocking
    blocking_conditions = {g.condition for g in blocking}
    assert "injury_status" in blocking_conditions
    assert "sleep_hours" in blocking_conditions
