"""
Methodologies API Routes

Endpoints for listing and retrieving methodologies.
"""

from fastapi import APIRouter, HTTPException, status
from pathlib import Path
import json
from typing import Dict

from src.api.models.responses import MethodologiesListResponse, MethodologyInfo
from src.schemas import MethodologyModelCard

router = APIRouter()

# Methodology file mapping
METHODOLOGY_MAP: Dict[str, Path] = {
    "polarized_80_20_v1": Path("models/methodology_polarized.json"),
    "threshold_70_20_10_v1": Path("models/methodology_threshold_70_20_10_v1.json"),
    "pyramidal_v1": Path("models/methodology_pyramidal_v1.json"),
}


def _load_methodology(methodology_id: str) -> MethodologyModelCard:
    """
    Load methodology from file by ID.

    Args:
        methodology_id: Methodology identifier

    Returns:
        MethodologyModelCard instance

    Raises:
        HTTPException: If methodology not found or invalid
    """
    if methodology_id not in METHODOLOGY_MAP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Methodology '{methodology_id}' not found. Available: {list(METHODOLOGY_MAP.keys())}",
        )

    methodology_path = METHODOLOGY_MAP[methodology_id]

    if not methodology_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Methodology file not found: {methodology_path}",
        )

    try:
        with open(methodology_path) as f:
            data = json.load(f)
        return MethodologyModelCard(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load methodology: {str(e)}",
        )


@router.get("/methodologies", response_model=MethodologiesListResponse)
async def list_methodologies() -> MethodologiesListResponse:
    """
    List all available methodologies.

    Returns brief information about each methodology including:
    - ID and name
    - Description
    - Base fragility score
    - Intensity distribution

    Returns:
        MethodologiesListResponse with list of methodologies
    """
    methodologies = []

    for methodology_id in METHODOLOGY_MAP.keys():
        try:
            methodology = _load_methodology(methodology_id)

            # Format intensity distribution as "low/threshold/high"
            dist_config = methodology.intensity_distribution_config
            intensity_dist = f"{int(dist_config.low_intensity_target * 100)}/{int(dist_config.threshold_intensity_target * 100)}/{int(dist_config.high_intensity_target * 100)}"

            methodologies.append(
                MethodologyInfo(
                    id=methodology.id,
                    name=methodology.name,
                    description=methodology.philosophy.one_line_description,
                    fragility_score=methodology.risk_profile.fragility_score,
                    intensity_distribution=intensity_dist,
                )
            )
        except Exception as e:
            # Skip methodologies that fail to load
            continue

    return MethodologiesListResponse(
        methodologies=methodologies, count=len(methodologies)
    )


@router.get("/methodologies/{methodology_id}", response_model=MethodologyModelCard)
async def get_methodology(methodology_id: str) -> MethodologyModelCard:
    """
    Get full methodology details by ID.

    Args:
        methodology_id: Methodology identifier (e.g., 'polarized', 'threshold_70_20_10_v1')

    Returns:
        Complete MethodologyModelCard with all assumptions, safety gates, and configurations
    """
    return _load_methodology(methodology_id)
