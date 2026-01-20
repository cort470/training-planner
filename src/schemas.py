"""
Pydantic models for training planner data validation.

This module defines the core data structures for:
- Methodology Model Cards: Training methodology definitions with assumptions and safety gates
- User Profiles: Athlete current state and training context
- Reasoning Traces: Decision logging and traceability
- Refusal Responses: Structured safety gate violation outputs
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Enumerations
# ============================================================================

class MetabolicFocus(str, Enum):
    """Primary energy systems targeted by a methodology."""
    AEROBIC_BASE = "aerobic_base"
    VO2MAX = "vo2max"
    LACTATE_THRESHOLD = "lactate_threshold"
    ANAEROBIC_CAPACITY = "anaerobic_capacity"
    NEUROMUSCULAR_POWER = "neuromuscular_power"


class Criticality(str, Enum):
    """How essential an assumption is to methodology safety/effectiveness."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, Enum):
    """Whether a safety gate violation triggers hard refusal or warning."""
    WARNING = "warning"
    BLOCKING = "blocking"


class StressLevel(str, Enum):
    """Self-reported non-training life stress."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class HRVTrend(str, Enum):
    """Heart rate variability trend direction."""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    UNKNOWN = "unknown"


class PrimaryGoal(str, Enum):
    """Main objective for current training block."""
    RACE_PERFORMANCE = "race_performance"
    BASE_BUILDING = "base_building"
    WEIGHT_LOSS = "weight_loss"
    GENERAL_FITNESS = "general_fitness"
    INJURY_PREVENTION = "injury_prevention"


class RaceDistance(str, Enum):
    """Standard triathlon race distances."""
    SPRINT = "sprint"
    OLYMPIC = "olympic"
    HALF_IRONMAN = "half_ironman"
    IRONMAN = "ironman"
    SEVENTY_THREE = "70.3"
    OTHER = "other"


class RacePriority(str, Enum):
    """Race importance level."""
    A = "A"  # Key race
    B = "B"  # Important
    C = "C"  # Training race


class Climate(str, Enum):
    """Training environment climate type."""
    HOT_HUMID = "hot_humid"
    HOT_DRY = "hot_dry"
    TEMPERATE = "temperate"
    COLD = "cold"
    VARIABLE = "variable"


class IntensityDistribution(str, Enum):
    """Preferred training intensity approach."""
    POLARIZED = "polarized"
    PYRAMIDAL = "pyramidal"
    THRESHOLD = "threshold"
    FLEXIBLE = "flexible"


class Weekday(str, Enum):
    """Days of the week."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class MenstrualPhase(str, Enum):
    """Menstrual cycle phases for female athletes."""
    FOLLICULAR = "follicular"
    OVULATION = "ovulation"
    LUTEAL = "luteal"
    MENSTRUATION = "menstruation"
    NOT_APPLICABLE = "not_applicable"


# ============================================================================
# Methodology Model Card Components
# ============================================================================

class Philosophy(BaseModel):
    """Core training philosophy and rationale for a methodology."""

    one_line_description: str = Field(
        ...,
        description="Concise summary of the methodology's approach"
    )

    core_logic: str = Field(
        ...,
        description="Detailed explanation of the underlying physiological rationale"
    )

    metabolic_focus: List[MetabolicFocus] = Field(
        default_factory=list,
        description="Primary energy systems targeted by this methodology"
    )


class Assumption(BaseModel):
    """
    Explicit assumption about athlete state required for methodology validity.

    Each assumption represents a prerequisite condition that must be satisfied
    for the methodology to be safe and effective.
    """

    key: str = Field(
        ...,
        description="Internal key for mapping to user input (must match UserProfile schema)"
    )

    expectation: str = Field(
        ...,
        description="Human-readable constraint description"
    )

    reasoning_justification: str = Field(
        ...,
        description="Why this assumption matters (used in reasoning trace)"
    )

    criticality: Criticality = Field(
        default=Criticality.MEDIUM,
        description="How essential this assumption is to methodology safety/effectiveness"
    )

    validation_rule: str = Field(
        ...,
        description="Pseudo-code or expression for validating this assumption"
    )


class ExclusionCriterion(BaseModel):
    """
    Circuit breaker configuration for a specific safety condition.

    Defines when plan generation must be refused and what action to take.
    """

    condition: str = Field(
        ...,
        description="The user profile field being evaluated"
    )

    threshold: str = Field(
        ...,
        description="The trigger value/expression for the circuit breaker"
    )

    severity: Severity = Field(
        ...,
        description="Whether this triggers a hard refusal or just a warning"
    )

    validation_logic: str = Field(
        ...,
        description="Pseudo-code for programmatic validation"
    )

    bridge_action: str = Field(
        ...,
        description="Specific recommendation when this gate triggers"
    )


class SafetyGates(BaseModel):
    """Circuit breaker configuration for a methodology."""

    exclusion_criteria: List[ExclusionCriterion] = Field(
        ...,
        min_length=1,
        description="List of conditions that trigger plan refusal"
    )

    refusal_bridge_template: str = Field(
        ...,
        description="Template for constructive refusal message with {placeholders}"
    )


class RiskProfile(BaseModel):
    """Characterization of methodology robustness and risk factors."""

    fragility_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Base fragility score (0=Robust, 1=Extremely Fragile)"
    )

    sensitivity_factors: List[str] = Field(
        ...,
        description="Variables that significantly impact plan success when changed"
    )

    fragility_calculation_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights for calculating user-specific fragility score"
    )


class FailureMode(BaseModel):
    """Known pattern of plan breakdown with early warnings and mitigation."""

    condition: str = Field(
        ...,
        description="Scenario that leads to plan failure"
    )

    early_warning_signals: List[str] = Field(
        ...,
        description="Observable indicators that this failure mode is developing"
    )

    mitigation_strategy: str = Field(
        ...,
        description="Recommended intervention to prevent full failure"
    )


class Reference(BaseModel):
    """Scientific literature or expert source supporting methodology."""

    citation: str = Field(
        ...,
        description="APA-style citation"
    )

    url: Optional[str] = Field(
        default=None,
        description="Link to source if available"
    )

    relevance: Optional[str] = Field(
        default=None,
        description="How this source supports the methodology"
    )


# ============================================================================
# Methodology Model Card (Main)
# ============================================================================

class MethodologyModelCard(BaseModel):
    """
    Complete specification of a training methodology.

    Defines the philosophy, assumptions, safety gates, and risk profile
    for a specific training approach. This is the "contract" between the
    methodology and the athlete.
    """

    id: str = Field(
        ...,
        pattern=r"^[a-z0-9_]+$",
        description="Unique identifier using snake_case"
    )

    name: str = Field(
        ...,
        description="Human-readable name of the methodology"
    )

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Semantic versioning (major.minor.patch)"
    )

    last_updated: date = Field(
        ...,
        description="Date of last model card revision"
    )

    philosophy: Philosophy = Field(
        ...,
        description="Core training philosophy and rationale"
    )

    assumptions: List[Assumption] = Field(
        ...,
        min_length=1,
        max_length=15,
        description="Explicit list of what this methodology assumes about the athlete"
    )

    safety_gates: SafetyGates = Field(
        ...,
        description="Circuit breaker configuration"
    )

    risk_profile: RiskProfile = Field(
        ...,
        description="Characterization of methodology robustness and risk factors"
    )

    failure_modes: Optional[List[FailureMode]] = Field(
        default=None,
        description="Known patterns of plan breakdown and early warning signals"
    )

    references: Optional[List[Reference]] = Field(
        default=None,
        description="Scientific literature or expert sources supporting methodology"
    )


# ============================================================================
# User Profile Components
# ============================================================================

class CurrentState(BaseModel):
    """Current physiological and contextual state of the athlete."""

    sleep_hours: float = Field(
        ...,
        ge=4.0,
        le=12.0,
        description="Average sleep hours per night over last 7 days"
    )

    sleep_consistency: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Standard deviation of sleep hours (lower = more consistent)"
    )

    injury_status: bool = Field(
        ...,
        description="Whether athlete has any active pain or injury requiring modification"
    )

    injury_details: Optional[str] = Field(
        default=None,
        description="Brief description of injury if injury_status is true"
    )

    stress_level: StressLevel = Field(
        ...,
        description="Self-reported non-training life stress over last 7 days"
    )

    stress_details: Optional[str] = Field(
        default=None,
        description="Optional context for stress level"
    )

    weekly_volume_hours: float = Field(
        ...,
        ge=0.0,
        le=40.0,
        description="Current average weekly training volume in hours"
    )

    volume_consistency_weeks: Optional[int] = Field(
        default=None,
        ge=0,
        le=52,
        description="Number of consecutive weeks at current volume (indicates base fitness)"
    )

    resting_heart_rate: Optional[int] = Field(
        default=None,
        ge=30,
        le=100,
        description="Average resting heart rate (bpm) over last 7 days"
    )

    hrv_trend: HRVTrend = Field(
        default=HRVTrend.UNKNOWN,
        description="Heart rate variability trend over last 14 days"
    )

    recent_illness: bool = Field(
        default=False,
        description="Any illness in last 14 days requiring training modification"
    )

    menstrual_cycle_phase: MenstrualPhase = Field(
        default=MenstrualPhase.NOT_APPLICABLE,
        description="Current phase for female athletes"
    )


class RaceResult(BaseModel):
    """Recent race result for fitness estimation."""

    race_date: date = Field(..., description="Race date", alias="date")
    distance: RaceDistance = Field(..., description="Race distance")
    finish_time: str = Field(
        ...,
        pattern=r"^\d{1,2}:\d{2}:\d{2}$",
        description="Finish time in HH:MM:SS format"
    )


class InjuryHistoryItem(BaseModel):
    """Previous injury record."""

    injury_type: str = Field(..., description="Type of injury")
    date_occurred: date = Field(..., description="When injury occurred")
    resolved: bool = Field(..., description="Whether injury is fully resolved")


class TrainingHistory(BaseModel):
    """Historical training context relevant to methodology selection."""

    years_training: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=50.0,
        description="Years of consistent endurance training"
    )

    recent_races: Optional[List[RaceResult]] = Field(
        default=None,
        description="Recent race results for fitness estimation"
    )

    injury_history: Optional[List[InjuryHistoryItem]] = Field(
        default=None,
        description="Previous injuries that may inform methodology selection"
    )


class Goals(BaseModel):
    """Training objectives and targets."""

    primary_goal: PrimaryGoal = Field(
        ...,
        description="Main objective for current training block"
    )

    race_date: Optional[date] = Field(
        default=None,
        description="Target race date (if race_performance is primary goal)"
    )

    race_distance: Optional[RaceDistance] = Field(
        default=None,
        description="Target race distance"
    )

    goal_finish_time: Optional[str] = Field(
        default=None,
        pattern=r"^\d{1,2}:\d{2}:\d{2}$",
        description="Target finish time in HH:MM:SS format"
    )

    weeks_to_race: Optional[int] = Field(
        default=None,
        ge=1,
        le=52,
        description="Number of weeks until target race"
    )

    priority_level: RacePriority = Field(
        default=RacePriority.B,
        description="Race priority (A=key race, B=important, C=training race)"
    )


class EquipmentAccess(BaseModel):
    """Available training equipment."""

    pool_access: bool = Field(default=True)
    bike_trainer: bool = Field(default=False)
    power_meter: bool = Field(default=False)
    heart_rate_monitor: bool = Field(default=True)


class EnvironmentalFactors(BaseModel):
    """Environmental training conditions."""

    climate: Optional[Climate] = Field(
        default=None,
        description="Training environment climate"
    )

    altitude_meters: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="Training altitude in meters above sea level"
    )


class Constraints(BaseModel):
    """External limitations on training capacity."""

    available_training_days: int = Field(
        default=6,
        ge=1,
        le=7,
        description="Days per week available for training"
    )

    max_session_duration_hours: float = Field(
        default=2.5,
        ge=0.5,
        le=8.0,
        description="Longest single session possible due to schedule"
    )

    equipment_access: Optional[EquipmentAccess] = Field(
        default=None,
        description="Available training equipment"
    )

    environmental_factors: Optional[EnvironmentalFactors] = Field(
        default=None,
        description="Environmental training conditions"
    )


class Preferences(BaseModel):
    """User preferences for plan generation."""

    preferred_intensity_distribution: Optional[IntensityDistribution] = Field(
        default=None,
        description="Preferred training intensity approach"
    )

    long_workout_day: Optional[Weekday] = Field(
        default=None,
        description="Preferred day for longest workout"
    )

    rest_day: Optional[Weekday] = Field(
        default=None,
        description="Preferred complete rest day"
    )


class Metadata(BaseModel):
    """Additional tracking information."""

    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when profile was created"
    )

    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last profile update"
    )

    notes: Optional[str] = Field(
        default=None,
        description="Free-form notes about current state"
    )


# ============================================================================
# User Profile (Main)
# ============================================================================

class UserProfile(BaseModel):
    """
    Athlete current state and training context.

    Used for methodology validation against safety gates and assumptions.
    This represents the athlete's current reality that must align with
    the methodology's requirements.
    """

    athlete_id: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for the athlete"
    )

    profile_date: date = Field(
        ...,
        description="Date this profile snapshot was created"
    )

    current_state: CurrentState = Field(
        ...,
        description="Current physiological and contextual state"
    )

    training_history: Optional[TrainingHistory] = Field(
        default=None,
        description="Historical training context"
    )

    goals: Goals = Field(
        ...,
        description="Training objectives and targets"
    )

    constraints: Optional[Constraints] = Field(
        default=None,
        description="External limitations on training capacity"
    )

    preferences: Optional[Preferences] = Field(
        default=None,
        description="User preferences for plan generation"
    )

    metadata: Optional[Metadata] = Field(
        default=None,
        description="Additional tracking information"
    )


# ============================================================================
# Reasoning Trace Components
# ============================================================================

class AssumptionCheck(BaseModel):
    """Record of a single assumption validation check."""

    assumption_key: str = Field(
        ...,
        description="Key from methodology assumption being checked"
    )

    passed: bool = Field(
        ...,
        description="Whether the check passed"
    )

    user_value: Optional[Any] = Field(
        default=None,
        description="Actual value from user profile"
    )

    threshold: Optional[Any] = Field(
        default=None,
        description="Required threshold from methodology"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of the check result"
    )


class GateViolation(BaseModel):
    """Record of a safety gate violation."""

    condition: str = Field(
        ...,
        description="Field that triggered the violation"
    )

    threshold: str = Field(
        ...,
        description="Threshold that was violated"
    )

    severity: Severity = Field(
        ...,
        description="Whether this is blocking or warning"
    )

    bridge: str = Field(
        ...,
        description="Actionable recommendation for remediation"
    )

    assumption_expectation: Optional[str] = Field(
        default=None,
        description="The violated assumption's expectation"
    )

    reasoning_justification: Optional[str] = Field(
        default=None,
        description="Why this assumption matters"
    )


class ReasoningTrace(BaseModel):
    """
    Complete decision trace from input to validation result.

    Documents every check, gate evaluation, and decision made during
    the validation process for full traceability.
    """

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this trace was generated"
    )

    methodology_id: str = Field(
        ...,
        description="ID of methodology being validated against"
    )

    athlete_id: str = Field(
        ...,
        description="ID of athlete being validated"
    )

    checks: List[AssumptionCheck] = Field(
        default_factory=list,
        description="All assumption checks performed"
    )

    safety_gates: List[GateViolation] = Field(
        default_factory=list,
        description="All safety gate violations found"
    )

    result: Literal["approved", "refused", "warning"] = Field(
        ...,
        description="Final validation decision"
    )

    fragility_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calculated fragility score (Phase 2)"
    )


# ============================================================================
# Refusal Response
# ============================================================================

class RefusalResponse(BaseModel):
    """
    Structured response when plan generation is refused.

    Contains all violations, actionable bridges, and reasoning trace reference.
    """

    status: Literal["refused", "warning", "approved"] = Field(
        ...,
        description="Validation outcome"
    )

    violations: List[GateViolation] = Field(
        default_factory=list,
        description="All safety gate violations found (sorted by severity)"
    )

    reasoning_trace_id: Optional[str] = Field(
        default=None,
        description="Filename of reasoning trace for this validation"
    )

    message: Optional[str] = Field(
        default=None,
        description="Summary message for the user"
    )


# ============================================================================
# Validation Result
# ============================================================================

class ValidationResult(BaseModel):
    """
    Complete result of validating a user profile against a methodology.

    Returned by the MethodologyValidator to communicate the outcome.
    """

    approved: bool = Field(
        ...,
        description="Whether validation passed and plan can be generated"
    )

    refusal_response: Optional[RefusalResponse] = Field(
        default=None,
        description="Detailed refusal information if validation failed"
    )

    reasoning_trace: ReasoningTrace = Field(
        ...,
        description="Complete decision trace"
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="Non-blocking warnings to show user"
    )
