"""
Sensitivity Analysis API Routes

Endpoints for what-if scenario analysis.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.models.requests import SensitivityRequest
from src.api.models.responses import SensitivityResponse
from src.api.routes.methodologies import _load_methodology
from src.validator import MethodologyValidator
from src.planner import TrainingPlanGenerator
from src.sensitivity import SensitivityAnalyzer

router = APIRouter()


@router.post("/sensitivity", response_model=SensitivityResponse)
async def analyze_sensitivity(request: SensitivityRequest) -> SensitivityResponse:
    """
    Perform sensitivity analysis (what-if scenario).

    Explores how changing a single assumption affects:
    - Fragility score
    - Validation status
    - Training plan characteristics (volume, intensity)

    Args:
        request: SensitivityRequest with baseline profile, methodology, assumption path, and new value

    Returns:
        SensitivityResponse with scenario results, fragility delta, and summary

    Raises:
        HTTPException: If methodology not found, analysis fails, or invalid assumption path
    """
    try:
        # Load methodology
        methodology = _load_methodology(request.methodology_id)

        # Validate baseline profile
        validator = MethodologyValidator(methodology)
        baseline_result = validator.validate(request.user_profile)

        # Generate baseline plan if approved
        baseline_plan = None
        if baseline_result.approved:
            generator = TrainingPlanGenerator(methodology, baseline_result)
            baseline_plan = generator.generate(request.user_profile)

        # Create analyzer
        analyzer = SensitivityAnalyzer(
            methodology, request.user_profile, baseline_result, baseline_plan
        )

        # Run scenario
        try:
            scenario_result = analyzer.modify_assumption(
                request.assumption_path, request.new_value
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid assumption path or value: {str(e)}",
            )

        # Build summary
        summary_parts = [
            f"Modified {request.assumption_path}: {scenario_result.original_value} → {scenario_result.new_value}",
        ]

        if scenario_result.new_fragility and scenario_result.original_fragility:
            delta = scenario_result.fragility_delta
            summary_parts.append(
                f"Fragility changed by {delta:+.3f} ({scenario_result.original_fragility:.2f} → {scenario_result.new_fragility:.2f})"
            )

        if scenario_result.validation_changed:
            summary_parts.append(
                f"Validation status changed to {scenario_result.new_validation_status}"
            )

        summary = ". ".join(summary_parts)

        # Build response
        return SensitivityResponse(
            scenario_result=scenario_result,
            fragility_delta=scenario_result.fragility_delta,
            validation_changed=scenario_result.validation_changed,
            summary=summary,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sensitivity analysis failed: {str(e)}",
        )
