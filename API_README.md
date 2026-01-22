# Training Planner API

FastAPI-based web API for the Human-in-the-Loop Training Planner.

## Overview

This API provides endpoints for:
- **Methodology Management**: List and retrieve training methodologies
- **Validation**: Validate user profiles against methodology assumptions
- **Fragility Analysis**: Calculate training plan risk scores
- **Plan Generation**: Generate personalized training plans
- **Sensitivity Analysis**: Run what-if scenarios

## Quick Start

### Start the API Server

```bash
python3 -m src.api.main
```

The server will start on `http://localhost:8000`.

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Methodologies

#### `GET /api/methodologies`
List all available training methodologies.

**Response:**
```json
{
  "methodologies": [
    {
      "id": "polarized_80_20_v1",
      "name": "Polarized 80/20 Training",
      "description": "80% low-intensity (Zone 1-2), 20% high-intensity (Zone 4-5) distribution",
      "fragility_score": 0.4,
      "intensity_distribution": "80/0/20"
    },
    ...
  ],
  "count": 3
}
```

#### `GET /api/methodologies/{methodology_id}`
Get full details for a specific methodology.

**Parameters:**
- `methodology_id`: One of `polarized_80_20_v1`, `threshold_70_20_10_v1`, `pyramidal_v1`

**Response:**
```json
{
  "id": "polarized_80_20_v1",
  "name": "Polarized 80/20 Training",
  "philosophy": {...},
  "assumptions": [...],
  "safety_gates": {...},
  "intensity_distribution_config": {...},
  ...
}
```

### Validation

#### `POST /api/validate`
Validate a user profile against a methodology's assumptions and safety gates.

**Request Body:**
```json
{
  "user_profile": {
    "athlete_id": "athlete_001",
    "current_state": {
      "sleep_hours": 8.0,
      "sleep_consistency": 0.8,
      "injury_status": false,
      "stress_level": "low",
      "weekly_volume_hours": 10.0,
      "volume_consistency_weeks": 6,
      "recent_illness": false,
      "hrv_trend": "stable"
    },
    "training_history": {
      "years_training": 2
    },
    "goals": {
      "primary_goal": "race_performance",
      "race_date": "2026-04-15",
      "race_distance": "olympic",
      "weeks_to_race": 12
    },
    "constraints": {
      "available_training_days": 6,
      "max_session_duration_hours": 2.5,
      "equipment_access": {
        "pool_access": true,
        "bike_trainer": true,
        "power_meter": false,
        "heart_rate_monitor": true
      }
    },
    "preferences": {
      "preferred_intensity_distribution": "polarized",
      "long_workout_day": "saturday",
      "rest_day": "sunday"
    }
  },
  "methodology_id": "polarized_80_20_v1"
}
```

**Response:**
```json
{
  "approved": true,
  "reasoning_trace": [
    "Methodology: polarized_80_20_v1 | Athlete: athlete_001",
    "[PASS] sleep_hours: User meets requirement",
    "[PASS] volume_consistency_weeks: User meets requirement",
    "Final Result: APPROVED"
  ],
  "warnings": [],
  "refusal_message": null,
  "validation_result": {...}
}
```

### Fragility Analysis

#### `POST /api/fragility`
Calculate fragility score for a user profile.

**Request Body:**
```json
{
  "user_profile": {...},  // Same as validation
  "methodology_id": "polarized_80_20_v1"
}
```

**Response:**
```json
{
  "score": 0.45,
  "interpretation": "Moderate Risk",
  "breakdown": {
    "sleep_deviation": 0.05,
    "stress_multiplier": 0.10,
    "volume_variance": 0.15,
    "intensity_frequency": 0.10,
    "recovery_quality": 0.05
  },
  "recommendations": [
    "Maintain consistent sleep schedule",
    "Monitor weekly volume progression"
  ],
  "fragility_result": {...}
}
```

### Plan Generation

#### `POST /api/plans`
Generate a complete training plan.

**Request Body:**
```json
{
  "user_profile": {...},  // Same as validation
  "methodology_id": "polarized_80_20_v1"
}
```

**Response:**
```json
{
  "plan": {
    "plan_duration_weeks": 12,
    "plan_start_date": "2026-01-27",
    "fragility_score": 0.45,
    "weeks": [
      {
        "week_number": 1,
        "phase": "base",
        "sessions": [
          {
            "day": "monday",
            "session_type": "run",
            "primary_zone": "zone_1",
            "duration_minutes": 60,
            "description": "Easy aerobic run",
            "workout_details": null
          },
          ...
        ]
      },
      ...
    ]
  },
  "validation_result": {...},
  "fragility_result": {...},
  "warnings": []
}
```

### Sensitivity Analysis

#### `POST /api/sensitivity`
Run what-if scenario by modifying an assumption.

**Request Body:**
```json
{
  "user_profile": {...},
  "methodology_id": "polarized_80_20_v1",
  "assumption_path": "current_state.sleep_hours",
  "new_value": 6.0
}
```

**Response:**
```json
{
  "scenario_result": {
    "modified_assumption": "current_state.sleep_hours",
    "original_value": 8.0,
    "new_value": 6.0,
    "original_fragility": 0.45,
    "new_fragility": 0.65,
    "fragility_delta": 0.20,
    "validation_changed": false,
    "new_validation_status": "approved"
  },
  "fragility_delta": 0.20,
  "validation_changed": false,
  "summary": "Modified current_state.sleep_hours: 8.0 → 6.0. Fragility changed by +0.200 (0.45 → 0.65)"
}
```

## Architecture

The API is a thin wrapper around the existing business logic:

```
FastAPI Routes
    ↓
Business Logic Layer
    - MethodologyValidator
    - FragilityCalculator
    - TrainingPlanGenerator
    - SensitivityAnalyzer
    ↓
Data Models (Pydantic v2)
    - UserProfile
    - MethodologyModelCard
    - TrainingPlan
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (validation failed, invalid input)
- `404`: Not Found (methodology doesn't exist)
- `500`: Internal Server Error

## CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (React dev server)
- `http://localhost:5173` (Vite dev server)

## Development

### Install Dependencies

```bash
pip3 install fastapi uvicorn[standard] python-multipart httpx
```

### Run in Development Mode

```bash
python3 -m src.api.main
```

The server runs with auto-reload enabled, so code changes trigger automatic restarts.

### Test the API

```bash
python3 test_api_simple.py
```

Or use the interactive docs at `http://localhost:8000/docs`.

## Production Deployment

For production, use a process manager like systemd, supervisord, or Docker:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Next Steps

- [ ] Add authentication/authorization
- [ ] Implement rate limiting
- [ ] Add request logging and monitoring
- [ ] Create Docker container
- [ ] Build React frontend
- [ ] Add caching layer (Redis)
- [ ] Implement batch plan generation
