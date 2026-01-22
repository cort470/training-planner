"""
Validation API Routes

Endpoints for user profile validation against methodologies.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.models.requests import ValidationRequest
from src.api.models.responses import ValidationResponse
from src.api.routes.methodologies import _load_methodology
from src.validator import MethodologyValidator

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
async def validate_profile(request: ValidationRequest) -> ValidationResponse:
    """
    Validate user profile against methodology assumptions and safety gates.

    Performs comprehensive validation including:
    - Assumption checking (sleep, stress, volume, etc.)
    - Safety gate evaluation (blocking vs warning conditions)
    - Reasoning trace generation

    Args:
        request: ValidationRequest with user profile and methodology ID

    Returns:
        ValidationResponse with approval status, reasoning, and warnings

    Raises:
        HTTPException: If methodology not found or validation fails unexpectedly
    """
    try:
        # Load methodology
        methodology = _load_methodology(request.methodology_id)

        # Create validator
        validator = MethodologyValidator(methodology)

        # Validate profile
        result = validator.validate(request.user_profile)

        # Extract refusal message from refusal_response if present
        refusal_message = None
        if result.refusal_response:
            refusal_message = result.refusal_response.message

        # Build reasoning trace from ReasoningTrace object
        trace = result.reasoning_trace
        reasoning_steps = []
        reasoning_steps.append(
            f"Methodology: {trace.methodology_id} | Athlete: {trace.athlete_id}"
        )

        for check in trace.checks:
            status_str = "PASS" if check.passed else "FAIL"
            reasoning_steps.append(
                f"[{status_str}] {check.assumption_key}: {check.reasoning}"
            )

        for gate in trace.safety_gates:
            reasoning_steps.append(
                f"[GATE] {gate.condition} violated (Severity: {gate.severity})"
            )

        reasoning_steps.append(f"Final Result: {trace.result.upper()}")

        # Build response
        return ValidationResponse(
            approved=result.approved,
            reasoning_trace=reasoning_steps,
            warnings=result.warnings,
            refusal_message=refusal_message,
            validation_result=result,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (methodology not found)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )
