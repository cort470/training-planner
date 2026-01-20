"""
Reasoning trace generation and export.

This module provides tools for documenting the complete decision-making
process during validation. Traces are exported to JSON and Markdown for
human review and auditability.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.schemas import (
    ReasoningTrace,
    AssumptionCheck,
    GateViolation,
    Severity,
)


class ReasoningTraceBuilder:
    """
    Builds and exports reasoning traces for validation decisions.

    The reasoning trace is the complete audit trail showing:
    - What assumptions were checked
    - What values were found
    - What safety gates were evaluated
    - What the final decision was

    This ensures full transparency and allows users to understand exactly
    why a plan was approved or refused.
    """

    def __init__(self, methodology_id: str, athlete_id: str):
        """
        Initialize trace builder.

        Args:
            methodology_id: ID of the methodology being validated
            athlete_id: ID of the athlete being validated
        """
        self.trace = ReasoningTrace(
            methodology_id=methodology_id,
            athlete_id=athlete_id,
            result="approved",  # Will be updated as checks run
        )

    def add_check(
        self,
        assumption_key: str,
        passed: bool,
        reasoning: str,
        user_value: Optional[any] = None,
        threshold: Optional[any] = None,
    ) -> None:
        """
        Add an assumption check to the trace.

        Args:
            assumption_key: The assumption being checked
            passed: Whether the check passed
            reasoning: Explanation of the check result
            user_value: Actual value from user profile
            threshold: Required threshold
        """
        check = AssumptionCheck(
            assumption_key=assumption_key,
            passed=passed,
            user_value=user_value,
            threshold=threshold,
            reasoning=reasoning,
        )
        self.trace.checks.append(check)

    def add_gate_trigger(
        self,
        condition: str,
        threshold: str,
        severity: Severity,
        bridge_action: str,
        assumption_expectation: Optional[str] = None,
        reasoning_justification: Optional[str] = None,
    ) -> None:
        """
        Add a safety gate violation to the trace.

        Args:
            condition: Field that triggered the violation
            threshold: Threshold that was violated
            severity: Whether blocking or warning
            bridge_action: Recommended action
            assumption_expectation: The violated assumption's expectation
            reasoning_justification: Why this assumption matters
        """
        violation = GateViolation(
            condition=condition,
            threshold=threshold,
            severity=severity,
            bridge=bridge_action,
            assumption_expectation=assumption_expectation,
            reasoning_justification=reasoning_justification,
        )
        self.trace.safety_gates.append(violation)

    def set_result(self, result: str) -> None:
        """
        Set the final validation result.

        Args:
            result: One of "approved", "refused", "warning"
        """
        self.trace.result = result

    def set_fragility_score(self, score: float) -> None:
        """
        Set the fragility score (Phase 2 feature).

        Args:
            score: Fragility score between 0.0 and 1.0
        """
        self.trace.fragility_score = score

    def add_fragility_calculation(
        self,
        base_fragility: float,
        breakdown: dict,
        interpretation: str,
        recommendations: list,
    ) -> None:
        """
        Add detailed fragility calculation to trace (Phase 2 feature).

        Args:
            base_fragility: Base fragility from methodology
            breakdown: Dictionary of penalty contributions by factor
            interpretation: Risk level interpretation
            recommendations: List of actionable recommendations
        """
        # Store in internal attributes for markdown export
        if not hasattr(self, "_fragility_details"):
            self._fragility_details = {}

        self._fragility_details = {
            "base": base_fragility,
            "breakdown": breakdown,
            "interpretation": interpretation,
            "recommendations": recommendations,
        }

    def add_plan_decision(
        self,
        decision_point: str,
        input_factors: list,
        reasoning: str,
        outcome: str,
    ) -> None:
        """
        Add a plan generation decision to trace (Phase 2 feature).

        Args:
            decision_point: The decision that was made
            input_factors: Factors that influenced this decision
            reasoning: Explanation of why this decision was made
            outcome: The resulting choice or action taken
        """
        if not hasattr(self, "_plan_decisions"):
            self._plan_decisions = []

        self._plan_decisions.append(
            {
                "decision_point": decision_point,
                "input_factors": input_factors,
                "reasoning": reasoning,
                "outcome": outcome,
            }
        )

    def export_to_json(self) -> dict:
        """
        Export trace to JSON-serializable dictionary.

        Returns:
            Dictionary representation of the trace
        """
        return self.trace.model_dump(mode="json")

    def export_to_markdown(self) -> str:
        """
        Export trace to human-readable Markdown format.

        Returns:
            Markdown-formatted trace report
        """
        lines = []

        # Header
        lines.append("# Reasoning Trace")
        lines.append("")
        lines.append(f"**Timestamp:** {self.trace.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Methodology:** `{self.trace.methodology_id}`")
        lines.append(f"**Athlete:** `{self.trace.athlete_id}`")
        lines.append(f"**Result:** **{self.trace.result.upper()}**")
        if self.trace.fragility_score is not None:
            lines.append(f"**Fragility Score:** {self.trace.fragility_score:.2f}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Assumption Checks
        lines.append("## Assumption Validation")
        lines.append("")

        if not self.trace.checks:
            lines.append("*No assumption checks performed*")
        else:
            passed_checks = [c for c in self.trace.checks if c.passed]
            failed_checks = [c for c in self.trace.checks if not c.passed]

            lines.append(
                f"**Summary:** {len(passed_checks)}/{len(self.trace.checks)} assumptions satisfied"
            )
            lines.append("")

            # Show failed checks first
            if failed_checks:
                lines.append("### ❌ Failed Checks")
                lines.append("")
                for check in failed_checks:
                    lines.append(f"#### `{check.assumption_key}`")
                    lines.append(f"- **User Value:** `{check.user_value}`")
                    if check.threshold is not None:
                        lines.append(f"- **Required:** `{check.threshold}`")
                    lines.append(f"- **Reasoning:** {check.reasoning}")
                    lines.append("")

            # Show passed checks
            if passed_checks:
                lines.append("### ✅ Passed Checks")
                lines.append("")
                for check in passed_checks:
                    lines.append(f"#### `{check.assumption_key}`")
                    lines.append(f"- **User Value:** `{check.user_value}`")
                    if check.threshold is not None:
                        lines.append(f"- **Required:** `{check.threshold}`")
                    lines.append(f"- **Reasoning:** {check.reasoning}")
                    lines.append("")

        lines.append("---")
        lines.append("")

        # Safety Gate Evaluation
        lines.append("## Safety Gate Evaluation")
        lines.append("")

        if not self.trace.safety_gates:
            lines.append("✅ **No safety gate violations detected**")
            lines.append("")
        else:
            blocking = [v for v in self.trace.safety_gates if v.severity == Severity.BLOCKING]
            warnings = [v for v in self.trace.safety_gates if v.severity == Severity.WARNING]

            lines.append(
                f"**Violations:** {len(blocking)} blocking, {len(warnings)} warnings"
            )
            lines.append("")

            # Show blocking violations
            if blocking:
                lines.append("### ⛔ Blocking Violations")
                lines.append("")
                for i, violation in enumerate(blocking, 1):
                    lines.append(f"#### {i}. {violation.condition}")
                    lines.append(f"- **Condition:** `{violation.condition} {violation.threshold}`")
                    if violation.assumption_expectation:
                        lines.append(f"- **Violated Assumption:** {violation.assumption_expectation}")
                    if violation.reasoning_justification:
                        lines.append(f"- **Why It Matters:** {violation.reasoning_justification}")
                    lines.append(f"- **Path Forward:** {violation.bridge}")
                    lines.append("")

            # Show warnings
            if warnings:
                lines.append("### ⚠️ Warnings")
                lines.append("")
                for i, violation in enumerate(warnings, 1):
                    lines.append(f"#### {i}. {violation.condition}")
                    lines.append(f"- **Condition:** `{violation.condition} {violation.threshold}`")
                    if violation.assumption_expectation:
                        lines.append(f"- **Violated Assumption:** {violation.assumption_expectation}")
                    lines.append(f"- **Recommendation:** {violation.bridge}")
                    lines.append("")

        lines.append("---")
        lines.append("")

        # Final Decision
        lines.append("## Final Decision")
        lines.append("")

        if self.trace.result == "approved":
            lines.append("✅ **APPROVED**")
            lines.append("")
            lines.append("All safety gates passed. The methodology is appropriate for the athlete's current state.")
        elif self.trace.result == "warning":
            lines.append("⚠️ **APPROVED WITH WARNINGS**")
            lines.append("")
            lines.append("Plan can proceed, but non-critical warnings were identified. Review recommendations above.")
        else:  # refused
            lines.append("⛔ **REFUSED**")
            lines.append("")
            lines.append("Plan generation refused due to safety gate violations. Address blocking conditions before proceeding.")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Fragility Calculation (if available)
        if hasattr(self, "_fragility_details"):
            lines.append("## Fragility Score Calculation")
            lines.append("")
            details = self._fragility_details

            lines.append(f"**Base Fragility:** {details['base']:.3f} (from methodology)")
            lines.append("")

            lines.append("| Sensitivity Factor | Contribution | Weighted Impact |")
            lines.append("|-------------------|--------------|----------------|")

            for factor, contribution in details["breakdown"].items():
                factor_display = factor.replace("_", " ").title()
                lines.append(
                    f"| {factor_display} | {contribution:+.4f} | {contribution * 100:+.2f}% |"
                )

            lines.append("")
            lines.append(
                f"**Final F-Score:** {self.trace.fragility_score:.3f} → **{details['interpretation']}**"
            )
            lines.append("")

            if details["recommendations"]:
                lines.append("**Recommendations:**")
                for i, rec in enumerate(details["recommendations"], 1):
                    lines.append(f"{i}. {rec}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Plan Generation Decisions (if available)
        if hasattr(self, "_plan_decisions") and self._plan_decisions:
            lines.append("## Plan Generation Decisions")
            lines.append("")

            for i, decision in enumerate(self._plan_decisions, 1):
                lines.append(f"### Decision {i}: {decision['decision_point']}")
                lines.append("")
                lines.append(f"**Input Factors:** {', '.join(decision['input_factors'])}")
                lines.append("")
                lines.append(f"**Reasoning:** {decision['reasoning']}")
                lines.append("")
                lines.append(f"**Outcome:** {decision['outcome']}")
                lines.append("")

            lines.append("---")
            lines.append("")

        lines.append("*This trace provides full transparency into the validation decision process.*")

        return "\n".join(lines)

    def save_to_file(self, output_dir: Path, format: str = "json") -> Path:
        """
        Save trace to file in specified format.

        Args:
            output_dir: Directory to save trace file
            format: Output format ("json" or "markdown")

        Returns:
            Path to saved file

        Raises:
            ValueError: If format is not supported
        """
        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp_str = self.trace.timestamp.strftime("%Y%m%d_%H%M%S")
        athlete_id = self.trace.athlete_id.replace(" ", "_")

        if format == "json":
            filename = f"trace_{athlete_id}_{timestamp_str}.json"
            filepath = output_dir / filename

            with open(filepath, "w") as f:
                json.dump(self.export_to_json(), f, indent=2, default=str)

        elif format == "markdown":
            filename = f"trace_{athlete_id}_{timestamp_str}.md"
            filepath = output_dir / filename

            with open(filepath, "w") as f:
                f.write(self.export_to_markdown())

        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'")

        return filepath

    @classmethod
    def from_validation_result(
        cls, result, methodology_id: str, athlete_id: str
    ) -> "ReasoningTraceBuilder":
        """
        Create trace builder from an existing ValidationResult.

        Args:
            result: ValidationResult from validator
            methodology_id: Methodology ID
            athlete_id: Athlete ID

        Returns:
            ReasoningTraceBuilder with trace populated
        """
        builder = cls(methodology_id, athlete_id)
        builder.trace = result.reasoning_trace
        return builder


def save_trace_from_result(
    result, output_dir: Path, format: str = "json"
) -> Path:
    """
    Convenience function to save trace from ValidationResult.

    Args:
        result: ValidationResult containing the trace
        output_dir: Directory to save trace
        format: Output format ("json" or "markdown")

    Returns:
        Path to saved file
    """
    builder = ReasoningTraceBuilder(
        methodology_id=result.reasoning_trace.methodology_id,
        athlete_id=result.reasoning_trace.athlete_id,
    )
    builder.trace = result.reasoning_trace

    return builder.save_to_file(output_dir, format)


def load_trace_from_file(filepath: Path) -> ReasoningTrace:
    """
    Load a reasoning trace from JSON file.

    Args:
        filepath: Path to trace JSON file

    Returns:
        ReasoningTrace object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Trace file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    try:
        trace = ReasoningTrace(**data)
    except Exception as e:
        raise ValueError(f"Invalid trace file: {e}")

    return trace
