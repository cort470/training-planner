"""
Tests for reasoning trace generation and export.

Ensures that traces are properly built and can be exported to JSON and Markdown.
"""

import json
from pathlib import Path
import tempfile

import pytest

from src.schemas import ReasoningTrace, Severity, ValidationResult
from src.trace import (
    ReasoningTraceBuilder,
    save_trace_from_result,
    load_trace_from_file,
)
from src.validator import MethodologyValidator


# Fixtures

@pytest.fixture
def trace_builder():
    """Create a basic trace builder."""
    return ReasoningTraceBuilder(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
    )


@pytest.fixture
def populated_trace_builder():
    """Create a trace builder with some data."""
    builder = ReasoningTraceBuilder(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
    )

    # Add some checks
    builder.add_check(
        assumption_key="sleep_hours",
        passed=True,
        reasoning="Sleep exceeds minimum requirement",
        user_value=8.0,
        threshold=7.0,
    )

    builder.add_check(
        assumption_key="injury_status",
        passed=True,
        reasoning="No injuries reported",
        user_value=False,
        threshold=False,
    )

    builder.set_result("approved")

    return builder


@pytest.fixture
def refusal_trace_builder():
    """Create a trace builder with refusal scenario."""
    builder = ReasoningTraceBuilder(
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_002",
    )

    # Add checks
    builder.add_check(
        assumption_key="sleep_hours",
        passed=True,
        reasoning="Sleep OK",
        user_value=8.0,
        threshold=7.0,
    )

    builder.add_check(
        assumption_key="injury_status",
        passed=False,
        reasoning="Injury present",
        user_value=True,
        threshold=False,
    )

    # Add violation
    builder.add_gate_trigger(
        condition="injury_status",
        threshold="true",
        severity=Severity.BLOCKING,
        bridge_action="Seek medical clearance from sports medicine professional",
        assumption_expectation="No active injuries or pain",
        reasoning_justification="Training through injury compromises form and delays healing",
    )

    builder.set_result("refused")

    return builder


# Tests

def test_trace_builder_initialization(trace_builder):
    """Test that trace builder initializes correctly."""
    assert trace_builder.trace.methodology_id == "polarized_80_20_v1"
    assert trace_builder.trace.athlete_id == "test_athlete_001"
    assert trace_builder.trace.result == "approved"
    assert len(trace_builder.trace.checks) == 0
    assert len(trace_builder.trace.safety_gates) == 0


def test_add_check(trace_builder):
    """Test adding assumption checks to trace."""
    trace_builder.add_check(
        assumption_key="sleep_hours",
        passed=True,
        reasoning="Sleep is adequate",
        user_value=8.0,
        threshold=7.0,
    )

    assert len(trace_builder.trace.checks) == 1
    check = trace_builder.trace.checks[0]
    assert check.assumption_key == "sleep_hours"
    assert check.passed is True
    assert check.user_value == 8.0
    assert check.threshold == 7.0


def test_add_gate_trigger(trace_builder):
    """Test adding safety gate violations to trace."""
    trace_builder.add_gate_trigger(
        condition="injury_status",
        threshold="true",
        severity=Severity.BLOCKING,
        bridge_action="Seek medical clearance",
    )

    assert len(trace_builder.trace.safety_gates) == 1
    violation = trace_builder.trace.safety_gates[0]
    assert violation.condition == "injury_status"
    assert violation.severity == Severity.BLOCKING


def test_set_result(trace_builder):
    """Test setting validation result."""
    trace_builder.set_result("refused")
    assert trace_builder.trace.result == "refused"

    trace_builder.set_result("approved")
    assert trace_builder.trace.result == "approved"


def test_set_fragility_score(trace_builder):
    """Test setting fragility score."""
    trace_builder.set_fragility_score(0.4)
    assert trace_builder.trace.fragility_score == 0.4


def test_export_to_json(populated_trace_builder):
    """Test exporting trace to JSON."""
    json_data = populated_trace_builder.export_to_json()

    assert isinstance(json_data, dict)
    assert json_data["methodology_id"] == "polarized_80_20_v1"
    assert json_data["athlete_id"] == "test_athlete_001"
    assert json_data["result"] == "approved"
    assert len(json_data["checks"]) == 2
    assert "timestamp" in json_data


def test_export_to_markdown_approved(populated_trace_builder):
    """Test exporting approved trace to Markdown."""
    markdown = populated_trace_builder.export_to_markdown()

    assert isinstance(markdown, str)
    assert "# Reasoning Trace" in markdown
    assert "polarized_80_20_v1" in markdown
    assert "test_athlete_001" in markdown
    assert "APPROVED" in markdown
    assert "sleep_hours" in markdown
    assert "No safety gate violations detected" in markdown


def test_export_to_markdown_refusal(refusal_trace_builder):
    """Test exporting refusal trace to Markdown."""
    markdown = refusal_trace_builder.export_to_markdown()

    assert isinstance(markdown, str)
    assert "# Reasoning Trace" in markdown
    assert "REFUSED" in markdown
    assert "injury_status" in markdown
    assert "Blocking Violations" in markdown
    assert "Seek medical clearance" in markdown


def test_save_to_file_json(populated_trace_builder):
    """Test saving trace to JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        filepath = populated_trace_builder.save_to_file(output_dir, format="json")

        # File should exist
        assert filepath.exists()
        assert filepath.suffix == ".json"

        # Should be valid JSON
        with open(filepath) as f:
            data = json.load(f)

        assert data["methodology_id"] == "polarized_80_20_v1"
        assert data["athlete_id"] == "test_athlete_001"


def test_save_to_file_markdown(populated_trace_builder):
    """Test saving trace to Markdown file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        filepath = populated_trace_builder.save_to_file(output_dir, format="markdown")

        # File should exist
        assert filepath.exists()
        assert filepath.suffix == ".md"

        # Should contain markdown content
        content = filepath.read_text()
        assert "# Reasoning Trace" in content


def test_save_to_file_invalid_format(populated_trace_builder):
    """Test that invalid format raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with pytest.raises(ValueError):
            populated_trace_builder.save_to_file(output_dir, format="xml")


def test_load_trace_from_file(populated_trace_builder):
    """Test loading trace from saved JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Save trace
        filepath = populated_trace_builder.save_to_file(output_dir, format="json")

        # Load it back
        loaded_trace = load_trace_from_file(filepath)

        assert loaded_trace.methodology_id == "polarized_80_20_v1"
        assert loaded_trace.athlete_id == "test_athlete_001"
        assert loaded_trace.result == "approved"
        assert len(loaded_trace.checks) == 2


def test_load_trace_from_nonexistent_file():
    """Test that loading from nonexistent file raises error."""
    with pytest.raises(FileNotFoundError):
        load_trace_from_file(Path("nonexistent_trace.json"))


def test_save_trace_from_validation_result():
    """Test saving trace from a validation result."""
    # Load methodology and user
    methodology_path = Path("models/methodology_polarized.json")
    validator = MethodologyValidator.from_file(methodology_path)

    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        profile_data = json.load(f)

    from src.schemas import UserProfile

    user_profile = UserProfile(**profile_data)

    # Run validation
    result = validator.validate(user_profile)

    # Save trace
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        filepath = save_trace_from_result(result, output_dir, format="json")

        # File should exist
        assert filepath.exists()

        # Should be valid trace
        with open(filepath) as f:
            data = json.load(f)

        assert data["methodology_id"] == "polarized_80_20_v1"
        assert data["athlete_id"] == "test_athlete_001"


def test_trace_markdown_formatting():
    """Test that markdown trace has proper formatting."""
    builder = ReasoningTraceBuilder(
        methodology_id="test_methodology",
        athlete_id="test_athlete",
    )

    # Add mixed results
    builder.add_check("check1", True, "Passed", 10.0, 5.0)
    builder.add_check("check2", False, "Failed", 3.0, 5.0)

    builder.add_gate_trigger(
        condition="test_condition",
        threshold="< 5.0",
        severity=Severity.BLOCKING,
        bridge_action="Fix this issue",
    )

    builder.set_result("refused")

    markdown = builder.export_to_markdown()

    # Check structure
    assert "# Reasoning Trace" in markdown
    assert "## Assumption Validation" in markdown
    assert "## Safety Gate Evaluation" in markdown
    assert "## Final Decision" in markdown

    # Check content
    assert "✅ Passed Checks" in markdown
    assert "❌ Failed Checks" in markdown
    assert "⛔ Blocking Violations" in markdown
    assert "Fix this issue" in markdown


def test_trace_timestamp_included():
    """Test that traces include timestamp."""
    builder = ReasoningTraceBuilder("test", "test")
    json_data = builder.export_to_json()

    assert "timestamp" in json_data
    assert json_data["timestamp"] is not None


def test_from_validation_result():
    """Test creating trace builder from validation result."""
    # Load methodology and user
    methodology_path = Path("models/methodology_polarized.json")
    validator = MethodologyValidator.from_file(methodology_path)

    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        profile_data = json.load(f)

    from src.schemas import UserProfile

    user_profile = UserProfile(**profile_data)

    # Run validation
    result = validator.validate(user_profile)

    # Create builder from result
    builder = ReasoningTraceBuilder.from_validation_result(
        result,
        methodology_id="polarized_80_20_v1",
        athlete_id="test_athlete_001",
    )

    assert builder.trace.methodology_id == "polarized_80_20_v1"
    assert builder.trace.athlete_id == "test_athlete_001"
    assert len(builder.trace.checks) > 0
