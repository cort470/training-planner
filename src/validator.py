"""
Methodology validation and circuit breaker logic.

This module implements the core safety mechanism for the training planner.
It evaluates user profiles against methodology assumptions and safety gates,
refusing to generate plans when safety conditions aren't met.
"""

import json
from pathlib import Path
from typing import List, Tuple, Any, Optional
from datetime import datetime

from src.schemas import (
    MethodologyModelCard,
    UserProfile,
    ValidationResult,
    RefusalResponse,
    ReasoningTrace,
    AssumptionCheck,
    GateViolation,
    Severity,
)


class MethodologyValidator:
    """
    Validates user profiles against methodology requirements.

    Implements the "Circuit Breaker" pattern - evaluates all safety gates
    and refuses plan generation when prerequisites aren't met. Returns
    structured refusal responses with actionable bridges.

    The validator checks ALL safety conditions even if one fails, allowing
    users to see the complete picture of what needs addressing.
    """

    def __init__(self, methodology: MethodologyModelCard):
        """
        Initialize validator with a methodology.

        Args:
            methodology: The training methodology to validate against
        """
        self.methodology = methodology

    @classmethod
    def from_file(cls, methodology_path: Path) -> "MethodologyValidator":
        """
        Load methodology from JSON file and create validator.

        Args:
            methodology_path: Path to methodology JSON file

        Returns:
            MethodologyValidator instance

        Raises:
            FileNotFoundError: If methodology file doesn't exist
            ValueError: If methodology JSON is invalid
        """
        if not methodology_path.exists():
            raise FileNotFoundError(f"Methodology file not found: {methodology_path}")

        with open(methodology_path, "r") as f:
            methodology_data = json.load(f)

        try:
            methodology = MethodologyModelCard(**methodology_data)
        except Exception as e:
            raise ValueError(f"Invalid methodology file: {e}")

        return cls(methodology)

    def validate(self, user_profile: UserProfile) -> ValidationResult:
        """
        Validate user profile against methodology requirements.

        This is the main entry point for validation. It:
        1. Checks all assumptions
        2. Evaluates all safety gates
        3. Generates reasoning trace
        4. Returns structured result with refusal response if needed

        Args:
            user_profile: The athlete's current state and context

        Returns:
            ValidationResult with approval status, violations, and reasoning trace
        """
        # Initialize reasoning trace
        trace = ReasoningTrace(
            methodology_id=self.methodology.id,
            athlete_id=user_profile.athlete_id,
            result="approved",  # Will update if violations found
        )

        # Step 1: Check all assumptions
        assumption_checks = self._check_assumptions(user_profile)
        trace.checks = assumption_checks

        # Step 2: Evaluate all safety gates
        violations = self._check_safety_gates(user_profile)
        trace.safety_gates = violations

        # Step 3: Determine result based on violations
        blocking_violations = [v for v in violations if v.severity == Severity.BLOCKING]
        warning_violations = [v for v in violations if v.severity == Severity.WARNING]

        # Step 4: Build validation result
        if blocking_violations:
            trace.result = "refused"
            refusal_response = self._build_refusal_response(violations)
            return ValidationResult(
                approved=False,
                refusal_response=refusal_response,
                reasoning_trace=trace,
                warnings=[],
            )
        elif warning_violations:
            trace.result = "warning"
            warnings = [
                f"⚠️ {v.condition}: {v.bridge}" for v in warning_violations
            ]
            return ValidationResult(
                approved=True,
                refusal_response=None,
                reasoning_trace=trace,
                warnings=warnings,
            )
        else:
            trace.result = "approved"
            return ValidationResult(
                approved=True,
                refusal_response=None,
                reasoning_trace=trace,
                warnings=[],
            )

    def _check_assumptions(self, user_profile: UserProfile) -> List[AssumptionCheck]:
        """
        Evaluate all methodology assumptions against user profile.

        Args:
            user_profile: The athlete's current state

        Returns:
            List of assumption check results
        """
        checks = []

        for assumption in self.methodology.assumptions:
            check = self._evaluate_assumption(assumption.key, user_profile)
            checks.append(check)

        return checks

    def _evaluate_assumption(
        self, assumption_key: str, user_profile: UserProfile
    ) -> AssumptionCheck:
        """
        Evaluate a single assumption against user profile.

        Args:
            assumption_key: The assumption key to evaluate
            user_profile: The athlete's current state

        Returns:
            AssumptionCheck result
        """
        # Get the assumption definition
        assumption = next(
            (a for a in self.methodology.assumptions if a.key == assumption_key),
            None,
        )

        if not assumption:
            return AssumptionCheck(
                assumption_key=assumption_key,
                passed=False,
                reasoning=f"Unknown assumption key: {assumption_key}",
            )

        # Get user value from profile
        user_value = self._get_user_value(assumption_key, user_profile)

        # Evaluate validation rule
        passed, threshold = self._evaluate_validation_rule(
            assumption.validation_rule, user_value
        )

        # Build reasoning
        if passed:
            reasoning = f"{assumption.expectation} - Satisfied. {assumption.reasoning_justification}"
        else:
            reasoning = f"{assumption.expectation} - NOT satisfied. {assumption.reasoning_justification}"

        return AssumptionCheck(
            assumption_key=assumption_key,
            passed=passed,
            user_value=user_value,
            threshold=threshold,
            reasoning=reasoning,
        )

    def _check_safety_gates(self, user_profile: UserProfile) -> List[GateViolation]:
        """
        Evaluate all safety gates for circuit breaker conditions.

        Checks EVERY safety gate even if one fails, collecting all violations
        so users can see the complete picture of what needs addressing.

        Args:
            user_profile: The athlete's current state

        Returns:
            List of all gate violations (sorted by severity: blocking first)
        """
        violations = []

        for criterion in self.methodology.safety_gates.exclusion_criteria:
            violation = self._evaluate_safety_gate(criterion, user_profile)
            if violation:
                violations.append(violation)

        # Sort violations: blocking first, then warnings
        violations.sort(key=lambda v: 0 if v.severity == Severity.BLOCKING else 1)

        return violations

    def _evaluate_safety_gate(
        self, criterion, user_profile: UserProfile
    ) -> Optional[GateViolation]:
        """
        Evaluate a single safety gate criterion.

        Args:
            criterion: The exclusion criterion to evaluate
            user_profile: The athlete's current state

        Returns:
            GateViolation if gate is triggered, None otherwise
        """
        # Get user value for the condition
        user_value = self._get_user_value(criterion.condition, user_profile)

        # Evaluate the threshold condition
        triggered = self._evaluate_threshold(
            criterion.threshold, user_value, criterion.validation_logic
        )

        if not triggered:
            return None

        # Find corresponding assumption for detailed reasoning
        assumption = next(
            (
                a
                for a in self.methodology.assumptions
                if a.key == criterion.condition
            ),
            None,
        )

        return GateViolation(
            condition=criterion.condition,
            threshold=criterion.threshold,
            severity=criterion.severity,
            bridge=criterion.bridge_action,
            assumption_expectation=assumption.expectation if assumption else None,
            reasoning_justification=(
                assumption.reasoning_justification if assumption else None
            ),
        )

    def _get_user_value(self, key: str, user_profile: UserProfile) -> Any:
        """
        Extract value from user profile for a given assumption key.

        Args:
            key: The field key to extract
            user_profile: The user profile

        Returns:
            The value from the profile, or None if not found
        """
        # Most values are in current_state
        if hasattr(user_profile.current_state, key):
            return getattr(user_profile.current_state, key)

        # Some might be in other sections
        if key == "weeks_to_race" and user_profile.goals.weeks_to_race:
            return user_profile.goals.weeks_to_race

        # Default to None if not found
        return None

    def _evaluate_validation_rule(
        self, validation_rule: str, user_value: Any
    ) -> Tuple[bool, Any]:
        """
        Evaluate a validation rule expression.

        Parses pseudo-code like "user.sleep_hours >= 7.0" and evaluates it.

        Args:
            validation_rule: The validation expression
            user_value: The actual user value

        Returns:
            Tuple of (passed: bool, threshold: Any)
        """
        # Remove "user." prefix if present
        validation_rule = validation_rule.replace("user.", "")

        # Parse common patterns
        # Handle compound range checks like "6.0 <= weekly_volume_hours <= 20.0"
        if "<=" in validation_rule and validation_rule.count("<=") == 2:
            # Split by variable name to get bounds
            parts = validation_rule.split("<=")
            lower = float(parts[0].strip())
            upper = float(parts[2].strip())
            passed = user_value is not None and lower <= user_value <= upper
            return passed, f"{lower}-{upper}"

        elif ">=" in validation_rule:
            parts = validation_rule.split(">=")
            threshold = float(parts[1].strip())
            passed = user_value is not None and user_value >= threshold
            return passed, threshold

        elif "==" in validation_rule:
            # Handle boolean checks
            if "false" in validation_rule.lower():
                threshold = False
                passed = user_value == False
                return passed, threshold
            elif "true" in validation_rule.lower():
                threshold = True
                passed = user_value == True
                return passed, threshold
            # Handle string checks
            else:
                parts = validation_rule.split("==")
                threshold = parts[1].strip().strip("'\"")
                passed = str(user_value) == threshold
                return passed, threshold

        elif " in " in validation_rule:
            # Handle list membership checks like "stress_level in ['low', 'moderate']"
            list_str = validation_rule.split(" in ")[1].strip()
            # Parse list string
            import ast

            try:
                threshold = ast.literal_eval(list_str)
                # Handle enum values
                user_val = user_value.value if hasattr(user_value, 'value') else user_value
                passed = user_val in threshold
                return passed, threshold
            except:
                return False, None

        elif "<=" in validation_rule:
            parts = validation_rule.split("<=")
            threshold = float(parts[1].strip())
            passed = user_value is not None and user_value <= threshold
            return passed, threshold

        # Default: couldn't parse
        return False, None

    def _evaluate_threshold(
        self, threshold_expr: str, user_value: Any, validation_logic: str
    ) -> bool:
        """
        Evaluate threshold expression for safety gate.

        Args:
            threshold_expr: Threshold expression (e.g., "< 6.0", "true", "== 'high'")
            user_value: Actual user value
            validation_logic: Full validation logic for context

        Returns:
            True if threshold is violated (gate triggered), False otherwise
        """
        threshold_expr = threshold_expr.strip()

        # Handle compound OR conditions FIRST (before simple operators)
        if " OR " in threshold_expr:
            # e.g., "< 6.0 OR > 20.0"
            parts = threshold_expr.split(" OR ")
            return any(
                self._evaluate_threshold(part.strip(), user_value, validation_logic)
                for part in parts
            )

        # Handle simple boolean
        if threshold_expr.lower() == "true":
            return user_value == True

        if threshold_expr.lower() == "false":
            return user_value == False

        # Handle comparison operators
        if threshold_expr.startswith("< "):
            threshold = float(threshold_expr[2:].strip())
            return user_value is not None and user_value < threshold

        if threshold_expr.startswith("<= "):
            threshold = float(threshold_expr[3:].strip())
            return user_value is not None and user_value <= threshold

        if threshold_expr.startswith("> "):
            threshold = float(threshold_expr[2:].strip())
            return user_value is not None and user_value > threshold

        if threshold_expr.startswith(">= "):
            threshold = float(threshold_expr[3:].strip())
            return user_value is not None and user_value >= threshold

        if threshold_expr.startswith("== "):
            target = threshold_expr[3:].strip().strip("'\"")
            return str(user_value) == target

        # Default: couldn't parse, assume not triggered
        return False

    def _build_refusal_response(
        self, violations: List[GateViolation]
    ) -> RefusalResponse:
        """
        Build structured refusal response from violations.

        Args:
            violations: List of all violations found

        Returns:
            RefusalResponse with formatted messages and bridges
        """
        blocking_violations = [
            v for v in violations if v.severity == Severity.BLOCKING
        ]
        warning_violations = [v for v in violations if v.severity == Severity.WARNING]

        status = "refused" if blocking_violations else "warning"

        # Build summary message
        if blocking_violations:
            message = f"⛔ Cannot generate training plan - {len(blocking_violations)} blocking condition(s) detected"
        else:
            message = f"⚠️ Plan can proceed with {len(warning_violations)} warning(s)"

        return RefusalResponse(
            status=status,
            violations=violations,
            message=message,
        )

    def generate_refusal_bridge(self, violation: GateViolation) -> str:
        """
        Generate formatted refusal bridge message for a violation.

        Uses the methodology's refusal bridge template with violation details.

        Args:
            violation: The gate violation

        Returns:
            Formatted refusal bridge message
        """
        template = self.methodology.safety_gates.refusal_bridge_template

        # Fill in template placeholders
        message = template.format(
            condition=violation.condition,
            threshold=violation.threshold,
            assumption_expectation=violation.assumption_expectation or "N/A",
            reasoning_justification=violation.reasoning_justification or "N/A",
            bridge_action=violation.bridge,
        )

        return message

    def display_validation_summary(self, result: ValidationResult) -> str:
        """
        Generate human-readable validation summary.

        Args:
            result: The validation result

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"VALIDATION REPORT: {self.methodology.name}")
        lines.append("=" * 70)
        lines.append("")

        if result.approved and not result.warnings:
            lines.append("✅ STATUS: APPROVED")
            lines.append("")
            lines.append(
                "All safety gates passed. Methodology is appropriate for current athlete state."
            )
        elif result.approved and result.warnings:
            lines.append("⚠️  STATUS: APPROVED WITH WARNINGS")
            lines.append("")
            lines.append("Plan can proceed, but consider these warnings:")
            for warning in result.warnings:
                lines.append(f"  • {warning}")
        else:
            lines.append("⛔ STATUS: REFUSED")
            lines.append("")
            lines.append(result.refusal_response.message)
            lines.append("")

            # Show each violation with bridge
            for i, violation in enumerate(result.refusal_response.violations, 1):
                if violation.severity == Severity.BLOCKING:
                    lines.append(f"\n{'─' * 70}")
                    lines.append(f"BLOCKING VIOLATION #{i}")
                    lines.append(f"{'─' * 70}")
                    lines.append(self.generate_refusal_bridge(violation))

        lines.append("")
        lines.append("=" * 70)
        lines.append(
            f"Timestamp: {result.reasoning_trace.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"Methodology: {result.reasoning_trace.methodology_id}")
        lines.append(f"Athlete: {result.reasoning_trace.athlete_id}")
        lines.append("=" * 70)

        return "\n".join(lines)
