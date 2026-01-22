"""
Fragility API Routes

Endpoints for fragility score calculation.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.models.requests import FragilityRequest
from src.api.models.responses import FragilityResponse
from src.api.routes.methodologies import _load_methodology
from src.fragility import FragilityCalculator

router = APIRouter()


@router.post("/fragility", response_model=FragilityResponse)
async def calculate_fragility(request: FragilityRequest) -> FragilityResponse:
    """
    Calculate fragility score for user profile.

    Fragility score (0.0-1.0) quantifies training plan risk based on:
    - Sleep deviation from baseline
    - Life stress multiplier
    - Volume variance
    - Intensity frequency
    - Recovery quality

    Lower scores indicate lower risk (more robust training capacity).
    Higher scores indicate higher risk (requires conservative approach).

    Args:
        request: FragilityRequest with user profile and methodology ID

    Returns:
        FragilityResponse with score, interpretation, breakdown, and recommendations

    Raises:
        HTTPException: If methodology not found or calculation fails
    """
    try:
        # Load methodology
        methodology = _load_methodology(request.methodology_id)

        # Create calculator
        calculator = FragilityCalculator(methodology)

        # Calculate fragility
        result = calculator.calculate(request.user_profile)

        # Build response
        return FragilityResponse(
            score=result.score,
            interpretation=result.interpretation,
            breakdown=result.breakdown,
            recommendations=result.recommendations,
            fragility_result=result,
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fragility calculation failed: {str(e)}",
        )
