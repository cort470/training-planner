"""
API Request Models

Pydantic models for API request validation.
"""

from typing import Any
from pydantic import BaseModel, Field

from src.schemas import UserProfile


class ValidationRequest(BaseModel):
    """Request model for profile validation."""

    user_profile: UserProfile = Field(..., description="User profile to validate")
    methodology_id: str = Field(
        ..., description="Methodology ID (e.g., 'polarized', 'threshold_70_20_10_v1')"
    )


class PlanGenerationRequest(BaseModel):
    """Request model for training plan generation."""

    user_profile: UserProfile = Field(..., description="User profile")
    methodology_id: str = Field(..., description="Methodology ID")


class FragilityRequest(BaseModel):
    """Request model for fragility calculation."""

    user_profile: UserProfile = Field(..., description="User profile")
    methodology_id: str = Field(..., description="Methodology ID")


class SensitivityRequest(BaseModel):
    """Request model for sensitivity analysis."""

    user_profile: UserProfile = Field(..., description="Baseline user profile")
    methodology_id: str = Field(..., description="Methodology ID")
    assumption_path: str = Field(
        ...,
        description="Dot-notation path to assumption (e.g., 'current_state.sleep_hours')",
    )
    new_value: Any = Field(..., description="New value for the assumption")
