"""
API Response Models

Pydantic models for API responses.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from src.validator import ValidationResult
from src.fragility import FragilityResult
from src.plan_schemas import TrainingPlan
from src.sensitivity import SensitivityResult


class MethodologyInfo(BaseModel):
    """Brief methodology information for listing."""

    id: str = Field(..., description="Methodology ID")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="One-line description")
    fragility_score: float = Field(..., description="Base fragility score (0.0-1.0)")
    intensity_distribution: str = Field(
        ..., description="Intensity distribution (e.g., '80/0/20')"
    )


class MethodologiesListResponse(BaseModel):
    """Response for GET /api/methodologies."""

    methodologies: List[MethodologyInfo] = Field(
        ..., description="List of available methodologies"
    )
    count: int = Field(..., description="Total number of methodologies")


class ValidationResponse(BaseModel):
    """Response for POST /api/validate."""

    approved: bool = Field(..., description="Whether profile is approved")
    reasoning_trace: List[str] = Field(..., description="Step-by-step reasoning")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    refusal_message: Optional[str] = Field(
        None, description="Refusal message if not approved"
    )
    validation_result: ValidationResult = Field(
        ..., description="Full validation result"
    )


class FragilityResponse(BaseModel):
    """Response for POST /api/fragility."""

    score: float = Field(..., description="Fragility score (0.0-1.0)")
    interpretation: str = Field(..., description="Human-readable interpretation")
    breakdown: Dict[str, float] = Field(..., description="Factor-wise breakdown")
    recommendations: List[str] = Field(..., description="Recommendations")
    fragility_result: FragilityResult = Field(..., description="Full fragility result")


class PlanGenerationResponse(BaseModel):
    """Response for POST /api/plans."""

    plan: TrainingPlan = Field(..., description="Generated training plan")
    validation_result: ValidationResult = Field(
        ..., description="Validation result used"
    )
    fragility_result: FragilityResult = Field(
        ..., description="Fragility calculation result"
    )
    warnings: List[str] = Field(default_factory=list, description="Plan warnings")


class SensitivityResponse(BaseModel):
    """Response for POST /api/sensitivity."""

    scenario_result: SensitivityResult = Field(
        ..., description="Sensitivity analysis result"
    )
    fragility_delta: float = Field(..., description="Change in fragility score")
    validation_changed: bool = Field(
        ..., description="Whether validation status changed"
    )
    summary: str = Field(..., description="Human-readable summary")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
