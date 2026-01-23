"""
Sensitivity analysis for exploring "what-if" scenarios.

This module allows users to modify profile assumptions and see how changes affect:
- Validation results (approved vs refused)
- Fragility scores
- Training plan adjustments
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.fragility import FragilityCalculator, FragilityResult
from src.plan_schemas import TrainingPlan
from src.planner import TrainingPlanGenerator
from src.schemas import MethodologyModelCard, UserProfile
from src.validator import MethodologyValidator, ValidationResult


class PlanAdjustmentSummary(BaseModel):
    """Summary of how a plan changed between baseline and modified scenario."""

    hi_sessions_per_week_delta: Optional[float] = Field(
        None, description="Change in average HI sessions per week"
    )
    volume_delta_hours: Optional[float] = Field(
        None, description="Change in average weekly volume (hours)"
    )
    phase_distribution_changed: bool = Field(
        default=False, description="Whether phase allocation changed"
    )
    intensity_distribution_delta: Optional[Dict[str, float]] = Field(
        None, description="Change in low/threshold/high intensity percentages"
    )


class SensitivityResult(BaseModel):
    """
    Result of a sensitivity analysis comparing baseline to modified scenario.

    Documents how a single assumption change affects validation, fragility, and plan.
    """

    modified_assumption: str = Field(
        ..., description="The assumption key that was modified (e.g., 'current_state.sleep_hours')"
    )
    original_value: Any = Field(..., description="Original value before modification")
    new_value: Any = Field(..., description="New value after modification")

    # Validation changes
    original_validation_status: str = Field(
        ..., description="Original validation result (approved/refused/warning)"
    )
    new_validation_status: str = Field(
        ..., description="New validation result after modification"
    )
    validation_changed: bool = Field(
        default=False, description="Whether validation status changed"
    )
    new_violations: Optional[List[str]] = Field(
        None, description="New safety gate violations (if any)"
    )

    # Fragility changes
    original_fragility: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Original fragility score"
    )
    new_fragility: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="New fragility score"
    )
    fragility_delta: Optional[float] = Field(
        None, description="Change in fragility score (new - original)"
    )

    # Plan changes
    plan_adjustments: Optional[PlanAdjustmentSummary] = Field(
        None, description="Summary of plan changes (if plan was regenerated)"
    )


class SensitivityAnalyzer:
    """
    Analyzes how profile assumption changes affect validation, fragility, and plans.

    Supports interactive "what-if" exploration:
    - "What if I get 7.5 hours of sleep instead of 6.5?"
    - "What if my stress level decreases to 'low'?"
    - "What if I increase my training volume?"
    """

    def __init__(
        self,
        methodology: MethodologyModelCard,
        baseline_profile: UserProfile,
        baseline_validation: ValidationResult,
        baseline_plan: Optional[TrainingPlan] = None,
    ):
        """
        Initialize the sensitivity analyzer.

        Args:
            methodology: The methodology model card
            baseline_profile: Original user profile
            baseline_validation: Original validation result
            baseline_plan: Original training plan (if generated)
        """
        self.methodology = methodology
        self.baseline_profile = baseline_profile
        self.baseline_validation = baseline_validation
        self.baseline_plan = baseline_plan

    def modify_assumption(
        self, assumption_key: str, new_value: Any
    ) -> SensitivityResult:
        """
        Modify a single assumption and analyze the impact.

        Args:
            assumption_key: Dot-notation path to the field (e.g., 'current_state.sleep_hours')
            new_value: New value for the field

        Returns:
            SensitivityResult with comparison of baseline vs modified scenario

        Raises:
            ValueError: If assumption_key is invalid or modification fails
        """
        # 1. Clone baseline profile (deep copy to ensure immutability)
        modified_profile = self.baseline_profile.model_copy(deep=True)

        # 2. Get original value
        original_value = self._get_nested_field(self.baseline_profile, assumption_key)

        # 3. Update specified field
        self._set_nested_field(modified_profile, assumption_key, new_value)

        # 4. Re-run validation
        validator = MethodologyValidator(self.methodology)
        new_validation = validator.validate(modified_profile)

        # 5. Check if validation status changed
        validation_changed = (
            self.baseline_validation.reasoning_trace.result
            != new_validation.reasoning_trace.result
        )

        # 6. Extract new violations (if any)
        new_violations = None
        if not new_validation.approved:
            new_violations = [
                gate.condition for gate in new_validation.reasoning_trace.safety_gates
            ]

        # 7. Recalculate fragility (if validation passes)
        new_fragility = None
        fragility_delta = None
        baseline_fragility = None

        if new_validation.approved:
            calculator = FragilityCalculator(self.methodology)
            fragility_result = calculator.calculate(modified_profile)
            new_fragility = fragility_result.score

            # Calculate baseline fragility if not already present
            if self.baseline_validation.approved:
                if self.baseline_validation.reasoning_trace.fragility_score is not None:
                    baseline_fragility = (
                        self.baseline_validation.reasoning_trace.fragility_score
                    )
                else:
                    # Calculate baseline fragility now
                    baseline_result = calculator.calculate(self.baseline_profile)
                    baseline_fragility = baseline_result.score

                # Calculate delta
                if baseline_fragility is not None:
                    fragility_delta = new_fragility - baseline_fragility

        # 8. Regenerate plan and compare (if both baseline and new pass validation)
        plan_adjustments = None
        if (
            new_validation.approved
            and self.baseline_validation.approved
            and self.baseline_plan is not None
        ):
            generator = TrainingPlanGenerator(self.methodology, new_validation)
            new_plan = generator.generate(modified_profile)
            plan_adjustments = self._compare_plans(self.baseline_plan, new_plan)

        return SensitivityResult(
            modified_assumption=assumption_key,
            original_value=original_value,
            new_value=new_value,
            original_validation_status=self.baseline_validation.reasoning_trace.result,
            new_validation_status=new_validation.reasoning_trace.result,
            validation_changed=validation_changed,
            new_violations=new_violations,
            original_fragility=baseline_fragility,
            new_fragility=new_fragility,
            fragility_delta=fragility_delta,
            plan_adjustments=plan_adjustments,
        )

    def _get_nested_field(self, obj: Any, path: str) -> Any:
        """
        Get a nested field value using dot notation.

        Args:
            obj: Object to traverse
            path: Dot-separated path (e.g., 'current_state.sleep_hours')

        Returns:
            Value at the specified path

        Raises:
            ValueError: If path is invalid
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise ValueError(f"Invalid path: {path} (failed at '{part}')")

        return current

    def _set_nested_field(self, obj: Any, path: str, value: Any) -> None:
        """
        Set a nested field value using dot notation.

        Args:
            obj: Object to modify
            path: Dot-separated path (e.g., 'current_state.sleep_hours')
            value: New value to set

        Raises:
            ValueError: If path is invalid
        """
        parts = path.split(".")
        current = obj

        # Traverse to the parent of the target field
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                raise ValueError(f"Invalid path: {path} (failed at '{part}')")

        # Set the final field
        final_field = parts[-1]
        if hasattr(current, final_field):
            setattr(current, final_field, value)
        else:
            raise ValueError(f"Invalid path: {path} (no field '{final_field}')")

    def _compare_plans(
        self, baseline_plan: TrainingPlan, new_plan: TrainingPlan
    ) -> PlanAdjustmentSummary:
        """
        Compare two plans and summarize the differences.

        Args:
            baseline_plan: Original plan
            new_plan: Modified plan

        Returns:
            PlanAdjustmentSummary with key differences
        """
        # Calculate average HI sessions per week for both plans
        baseline_hi_avg = self._calculate_avg_hi_sessions(baseline_plan)
        new_hi_avg = self._calculate_avg_hi_sessions(new_plan)
        hi_delta = new_hi_avg - baseline_hi_avg

        # Calculate average weekly volume
        baseline_volume_avg = baseline_plan.get_average_weekly_volume()
        new_volume_avg = new_plan.get_average_weekly_volume()
        volume_delta = new_volume_avg - baseline_volume_avg

        # Check if phase distribution changed
        baseline_phases = baseline_plan.get_phase_breakdown()
        new_phases = new_plan.get_phase_breakdown()
        phase_changed = baseline_phases != new_phases

        # Calculate intensity distribution delta
        baseline_intensity = baseline_plan.intensity_distribution
        new_intensity = new_plan.intensity_distribution

        intensity_delta = None
        if baseline_intensity and new_intensity:
            intensity_delta = {
                "low_intensity": new_intensity.low_intensity_percent
                - baseline_intensity.low_intensity_percent,
                "threshold": new_intensity.threshold_percent
                - baseline_intensity.threshold_percent,
                "high_intensity": new_intensity.high_intensity_percent
                - baseline_intensity.high_intensity_percent,
            }

        return PlanAdjustmentSummary(
            hi_sessions_per_week_delta=hi_delta if abs(hi_delta) > 0.01 else None,
            volume_delta_hours=volume_delta if abs(volume_delta) > 0.1 else None,
            phase_distribution_changed=phase_changed,
            intensity_distribution_delta=intensity_delta,
        )

    def _calculate_avg_hi_sessions(self, plan: TrainingPlan) -> float:
        """
        Calculate average number of high-intensity sessions per week.

        Args:
            plan: Training plan to analyze

        Returns:
            Average HI sessions per week
        """
        from src.plan_schemas import HIGH_INTENSITY_ZONES

        total_hi_sessions = 0
        for week in plan.weeks:
            hi_sessions = [
                s
                for s in week.sessions
                if s.primary_zone in HIGH_INTENSITY_ZONES
            ]
            total_hi_sessions += len(hi_sessions)

        return total_hi_sessions / len(plan.weeks) if plan.weeks else 0.0
