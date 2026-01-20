"""
Data schemas for training plan generation.

This module contains Pydantic models for representing structured training plans,
including weekly schedules, individual sessions, and plan metadata.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class IntensityZone(str, Enum):
    """Training intensity zones based on polarized methodology."""

    ZONE_1 = "zone_1"  # Easy aerobic (60-70% max HR)
    ZONE_2 = "zone_2"  # Moderate aerobic (70-80% max HR)
    ZONE_3 = "zone_3"  # Tempo/threshold (80-85% max HR) - minimized in polarized
    ZONE_4 = "zone_4"  # VO2max intervals (85-95% max HR)
    ZONE_5 = "zone_5"  # Anaerobic/sprint (95-100% max HR)
    REST = "rest"  # Complete rest day


class SessionType(str, Enum):
    """Types of training sessions."""

    SWIM = "swim"
    BIKE = "bike"
    RUN = "run"
    BRICK = "brick"  # Combined bike-run transition workout
    STRENGTH = "strength"
    REST = "rest"


class Weekday(str, Enum):
    """Days of the week."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TrainingPhase(str, Enum):
    """Training plan phases."""

    BASE = "base"  # Build aerobic foundation
    BUILD = "build"  # Increase intensity and volume
    PEAK = "peak"  # Maximum intensity
    TAPER = "taper"  # Recovery before race


class TrainingSession(BaseModel):
    """
    Individual training session within a week.

    Represents a single workout with intensity zone, duration, and description.
    """

    day: Weekday = Field(..., description="Day of the week for this session")
    session_type: SessionType = Field(..., description="Type of workout")
    primary_zone: IntensityZone = Field(
        ..., description="Primary training intensity zone"
    )
    duration_minutes: int = Field(
        ..., gt=0, description="Total session duration in minutes"
    )
    description: str = Field(
        ..., min_length=10, description="Human-readable workout description"
    )
    workout_details: Optional[str] = Field(
        None, description="Additional structured workout details (intervals, sets, etc.)"
    )

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Ensure duration is reasonable (5 min to 6 hours)."""
        if v < 5:
            raise ValueError("Session duration must be at least 5 minutes")
        if v > 360:  # 6 hours
            raise ValueError("Session duration cannot exceed 6 hours (360 minutes)")
        return v


class TrainingWeek(BaseModel):
    """
    Single week of training within a plan.

    Contains all sessions for one week, along with volume and phase metadata.
    """

    week_number: int = Field(..., ge=1, description="Week number in the plan (1-based)")
    phase: TrainingPhase = Field(..., description="Training phase for this week")
    total_volume_hours: float = Field(
        ..., gt=0, description="Total training volume for this week (hours)"
    )
    sessions: List[TrainingSession] = Field(
        ..., min_length=1, description="All training sessions for this week"
    )
    week_notes: Optional[str] = Field(
        None, description="Coach notes or guidance for the week"
    )

    @field_validator("total_volume_hours")
    @classmethod
    def validate_volume(cls, v: float) -> float:
        """Ensure weekly volume is reasonable (1-30 hours)."""
        if v < 1.0:
            raise ValueError("Weekly volume must be at least 1 hour")
        if v > 30.0:
            raise ValueError("Weekly volume cannot exceed 30 hours")
        return v

    @field_validator("sessions")
    @classmethod
    def validate_sessions_per_week(cls, v: List[TrainingSession]) -> List[TrainingSession]:
        """Ensure at most 7 sessions per week (one per day)."""
        if len(v) > 7:
            raise ValueError("Cannot have more than 7 sessions per week")

        # Check for duplicate days
        days_used = [session.day for session in v]
        if len(days_used) != len(set(days_used)):
            raise ValueError("Cannot have multiple sessions on the same day")

        return v

    def get_intensity_distribution(self) -> dict:
        """
        Calculate the intensity distribution for this week.

        Returns:
            Dictionary with percentages of volume in each zone category:
            - low_intensity: Zone 1-2 (easy aerobic)
            - threshold: Zone 3 (tempo)
            - high_intensity: Zone 4-5 (VO2max/anaerobic)
        """
        total_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone != IntensityZone.REST
        )

        if total_minutes == 0:
            return {"low_intensity": 0.0, "threshold": 0.0, "high_intensity": 0.0}

        low_intensity_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone in [IntensityZone.ZONE_1, IntensityZone.ZONE_2]
        )

        threshold_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone == IntensityZone.ZONE_3
        )

        high_intensity_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone in [IntensityZone.ZONE_4, IntensityZone.ZONE_5]
        )

        return {
            "low_intensity": (low_intensity_minutes / total_minutes) * 100,
            "threshold": (threshold_minutes / total_minutes) * 100,
            "high_intensity": (high_intensity_minutes / total_minutes) * 100,
        }


class IntensityDistributionSummary(BaseModel):
    """Summary of intensity distribution across the entire plan."""

    low_intensity_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in Zone 1-2"
    )
    threshold_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in Zone 3"
    )
    high_intensity_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in Zone 4-5"
    )

    @field_validator("low_intensity_percent", "threshold_percent", "high_intensity_percent")
    @classmethod
    def validate_sum(cls, v: float, info) -> float:
        """Validate that percentages sum to approximately 100%."""
        # Note: This validator runs per-field, full validation happens in model_validator
        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Validate total is approximately 100%
        total = (
            self.low_intensity_percent
            + self.threshold_percent
            + self.high_intensity_percent
        )
        if not (99.0 <= total <= 101.0):  # Allow 1% tolerance for rounding
            raise ValueError(
                f"Intensity distribution percentages must sum to 100%, got {total:.1f}%"
            )


class PlanDecision(BaseModel):
    """
    Documents a specific decision made during plan generation.

    Used for reasoning trace to explain why certain choices were made.
    """

    decision_point: str = Field(
        ..., min_length=5, description="The decision that was made"
    )
    input_factors: List[str] = Field(
        ..., min_length=1, description="Factors that influenced this decision"
    )
    reasoning: str = Field(
        ..., min_length=20, description="Explanation of why this decision was made"
    )
    outcome: str = Field(
        ..., min_length=10, description="The resulting choice or action taken"
    )


class TrainingPlan(BaseModel):
    """
    Complete multi-week training plan.

    Contains all weeks, sessions, and metadata for a structured training program.
    """

    athlete_id: str = Field(..., min_length=1, description="Unique athlete identifier")
    methodology_id: str = Field(
        ..., min_length=1, description="Methodology used to generate this plan"
    )
    plan_start_date: date = Field(..., description="Date when the plan begins")
    plan_duration_weeks: int = Field(
        ..., ge=1, le=52, description="Total duration of the plan in weeks"
    )
    race_date: Optional[date] = Field(None, description="Target race date if applicable")
    race_distance: Optional[str] = Field(
        None, description="Target race distance (sprint, olympic, etc.)"
    )
    weeks: List[TrainingWeek] = Field(
        ..., min_length=1, description="All weeks in the plan"
    )
    fragility_score: float = Field(
        ..., ge=0.0, le=1.0, description="Athlete fragility score at plan creation"
    )
    intensity_distribution: Optional[IntensityDistributionSummary] = Field(
        None, description="Overall intensity distribution summary"
    )
    plan_decisions: List[PlanDecision] = Field(
        default_factory=list,
        description="Key decisions made during plan generation (for reasoning trace)",
    )
    assumptions_used: dict = Field(
        ..., description="User profile assumptions at time of plan generation"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when plan was created"
    )
    notes: Optional[str] = Field(None, description="General notes about the plan")

    @field_validator("weeks")
    @classmethod
    def validate_weeks_count(cls, v: List[TrainingWeek], info) -> List[TrainingWeek]:
        """Ensure weeks count matches plan_duration_weeks."""
        # Note: plan_duration_weeks may not be available yet during construction
        if "plan_duration_weeks" in info.data:
            expected_weeks = info.data["plan_duration_weeks"]
            if len(v) != expected_weeks:
                raise ValueError(
                    f"Expected {expected_weeks} weeks but got {len(v)} weeks"
                )

        # Validate week numbering is sequential starting from 1
        for i, week in enumerate(v, start=1):
            if week.week_number != i:
                raise ValueError(
                    f"Week numbering must be sequential. Expected week {i}, got week {week.week_number}"
                )

        return v

    def calculate_intensity_distribution(self) -> IntensityDistributionSummary:
        """
        Calculate the overall intensity distribution across the entire plan.

        Returns:
            IntensityDistributionSummary with percentages for low/threshold/high intensity.
        """
        total_low_minutes = 0.0
        total_threshold_minutes = 0.0
        total_high_minutes = 0.0

        for week in self.weeks:
            for session in week.sessions:
                if session.primary_zone == IntensityZone.REST:
                    continue

                if session.primary_zone in [IntensityZone.ZONE_1, IntensityZone.ZONE_2]:
                    total_low_minutes += session.duration_minutes
                elif session.primary_zone == IntensityZone.ZONE_3:
                    total_threshold_minutes += session.duration_minutes
                elif session.primary_zone in [IntensityZone.ZONE_4, IntensityZone.ZONE_5]:
                    total_high_minutes += session.duration_minutes

        total_minutes = total_low_minutes + total_threshold_minutes + total_high_minutes

        if total_minutes == 0:
            return IntensityDistributionSummary(
                low_intensity_percent=0.0,
                threshold_percent=0.0,
                high_intensity_percent=0.0,
            )

        return IntensityDistributionSummary(
            low_intensity_percent=(total_low_minutes / total_minutes) * 100,
            threshold_percent=(total_threshold_minutes / total_minutes) * 100,
            high_intensity_percent=(total_high_minutes / total_minutes) * 100,
        )

    def get_average_weekly_volume(self) -> float:
        """Calculate average weekly training volume in hours."""
        if not self.weeks:
            return 0.0
        return sum(week.total_volume_hours for week in self.weeks) / len(self.weeks)

    def get_phase_breakdown(self) -> dict:
        """
        Get the number of weeks in each training phase.

        Returns:
            Dictionary mapping phase names to week counts.
        """
        phase_counts = {}
        for week in self.weeks:
            phase_name = week.phase.value
            phase_counts[phase_name] = phase_counts.get(phase_name, 0) + 1
        return phase_counts
