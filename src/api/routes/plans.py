"""
Training Plans API Routes

Endpoints for training plan generation.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.models.requests import PlanGenerationRequest
from src.api.models.responses import PlanGenerationResponse
from src.api.routes.methodologies import _load_methodology
from src.validator import MethodologyValidator
from src.fragility import FragilityCalculator
from src.planner import TrainingPlanGenerator

router = APIRouter()


@router.post("/plans", response_model=PlanGenerationResponse)
async def generate_plan(request: PlanGenerationRequest) -> PlanGenerationResponse:
    """
    Generate training plan for user profile.

    Complete workflow:
    1. Validate user profile against methodology
    2. Calculate fragility score
    3. Generate personalized training plan
    4. Return plan with validation and fragility results

    Plan generation will FAIL if validation is not approved.

    Args:
        request: PlanGenerationRequest with user profile and methodology ID

    Returns:
        PlanGenerationResponse with training plan, validation, and fragility results

    Raises:
        HTTPException: If validation fails, methodology not found, or generation fails
    """
    try:
        # Load methodology
        methodology = _load_methodology(request.methodology_id)

        # Validate profile
        validator = MethodologyValidator(methodology)
        validation_result = validator.validate(request.user_profile)

        # Check if validation passed
        if not validation_result.approved:
            refusal_msg = (
                validation_result.refusal_response.message
                if validation_result.refusal_response
                else "Validation failed"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation Failed",
                    "message": "User profile does not meet methodology requirements",
                    "refusal_message": refusal_msg,
                    "reasoning_trace": [
                        f"{check.assumption_key}: {check.reasoning}"
                        for check in validation_result.reasoning_trace.checks
                    ],
                },
            )

        # Calculate fragility
        calculator = FragilityCalculator(methodology)
        fragility_result = calculator.calculate(request.user_profile)

        # Generate plan
        generator = TrainingPlanGenerator(methodology, validation_result)
        plan = generator.generate(request.user_profile)

        # Start with warnings from validation
        warnings = validation_result.warnings.copy()

        # Add fragility-based warnings
        if fragility_result.score >= 0.6:
            warnings.append(
                f"High fragility score ({fragility_result.score:.2f}) - plan includes conservative intensity progression"
            )

        # Build response
        return PlanGenerationResponse(
            plan=plan,
            validation_result=validation_result,
            fragility_result=fragility_result,
            warnings=warnings,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}",
        )
