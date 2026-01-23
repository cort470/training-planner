"""
Data schemas for training plan generation.

This module contains Pydantic models for representing structured training plans,
including weekly schedules, individual sessions, and plan metadata.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class IntensityZone(str, Enum):
    """Training intensity zones based on physiological targets."""

    ACTIVE_RECOVERY = "active_recovery"  # Very easy, promotes blood flow (<60% max HR)
    ENDURANCE = "endurance"  # Aerobic base building (60-75% max HR)
    TEMPO = "tempo"  # Moderate sustained effort (76-85% max HR)
    THRESHOLD = "threshold"  # Lactate threshold (85-90% max HR)
    VO2MAX = "vo2max"  # Maximal aerobic capacity (90-95% max HR)
    ANAEROBIC = "anaerobic"  # Above lactate threshold (95-100% max HR)
    SPRINT = "sprint"  # Neuromuscular / max power (all-out)
    REST = "rest"  # Complete rest day


# Zone groupings for intensity distribution calculations
LOW_INTENSITY_ZONES = [IntensityZone.ACTIVE_RECOVERY, IntensityZone.ENDURANCE]
THRESHOLD_ZONES = [IntensityZone.TEMPO, IntensityZone.THRESHOLD]
HIGH_INTENSITY_ZONES = [IntensityZone.VO2MAX, IntensityZone.ANAEROBIC, IntensityZone.SPRINT]


class SessionType(str, Enum):
    """Types of training sessions."""

    SWIM = "swim"
    BIKE = "bike"
    RUN = "run"
    BRICK = "brick"  # Combined bike-run transition workout
    STRENGTH = "strength"
    REST = "rest"


# Sport-specific zone display mappings for user-facing descriptions
ZONE_DISPLAY = {
    SessionType.BIKE: {  # Coggan 7-zone power model - direct mapping
        IntensityZone.ACTIVE_RECOVERY: "Z1 (Recovery) - <55% FTP",
        IntensityZone.ENDURANCE: "Z2 (Endurance) - 56-75% FTP",
        IntensityZone.TEMPO: "Z3 (Tempo) - 76-90% FTP",
        IntensityZone.THRESHOLD: "Z4 (Threshold) - 91-105% FTP",
        IntensityZone.VO2MAX: "Z5 (VO2max) - 106-120% FTP",
        IntensityZone.ANAEROBIC: "Z6 (Anaerobic) - 121-150% FTP",
        IntensityZone.SPRINT: "Z7 (Neuromuscular) - max power",
    },
    SessionType.RUN: {  # Pace-based zones
        IntensityZone.ACTIVE_RECOVERY: "Recovery pace - very easy",
        IntensityZone.ENDURANCE: "Easy pace - conversational",
        IntensityZone.TEMPO: "Tempo pace - comfortably hard",
        IntensityZone.THRESHOLD: "Threshold pace - sustainable 60min",
        IntensityZone.VO2MAX: "VO2max pace - 3-8min race effort",
        IntensityZone.ANAEROBIC: "Repetition pace - 1-2min max effort",
        IntensityZone.SPRINT: "Sprint - all-out strides/sprints",
    },
    SessionType.SWIM: {  # CSS-based zones
        IntensityZone.ACTIVE_RECOVERY: "Recovery - easy drill work",
        IntensityZone.ENDURANCE: "Endurance - CSS pace -10sec/100m",
        IntensityZone.TEMPO: "Tempo - CSS pace -5sec/100m",
        IntensityZone.THRESHOLD: "Threshold - CSS pace",
        IntensityZone.VO2MAX: "VO2max - CSS pace +5sec/100m",
        IntensityZone.ANAEROBIC: "Anaerobic - near max 100m pace",
        IntensityZone.SPRINT: "Sprint - all-out 25m/50m",
    },
}


def get_zone_display(session_type: SessionType, zone: IntensityZone) -> str:
    """Get the sport-specific display string for a zone."""
    if session_type in ZONE_DISPLAY and zone in ZONE_DISPLAY[session_type]:
        return ZONE_DISPLAY[session_type][zone]
    return zone.value


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


class WeekType(str, Enum):
    """Classification of week within mesocycle."""

    LOAD = "load"  # Normal training week with progressive overload
    RECOVERY = "recovery"  # Deload/recovery week with reduced volume


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

    # Adherence tracking (populated after activity sync)
    actual_activity_id: Optional[int] = Field(
        None,
        description="Database ID of completed activity (if matched)"
    )

    adherence_status: Optional[Literal["completed", "partial", "missed", "unscheduled"]] = Field(
        None,
        description="Status after comparing to actual activity"
    )

    adherence_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Comparison metrics: duration_delta, zone_match, etc."
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

    # Mesocycle/periodization fields
    week_type: WeekType = Field(
        default=WeekType.LOAD,
        description="Whether this is a load or recovery week"
    )

    mesocycle_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Which mesocycle this week belongs to (1-based)"
    )

    mesocycle_week: Optional[int] = Field(
        default=None,
        ge=1,
        le=6,
        description="Week position within mesocycle (1-4 for 3:1, 1-3 for 2:1)"
    )

    volume_multiplier: float = Field(
        default=1.0,
        ge=0.0,
        le=1.5,
        description="Volume adjustment multiplier applied (e.g., 0.55 for recovery)"
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
            - low_intensity: Active Recovery + Endurance (easy aerobic)
            - threshold: Tempo + Threshold
            - high_intensity: VO2max + Anaerobic + Sprint
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
            if session.primary_zone in LOW_INTENSITY_ZONES
        )

        threshold_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone in THRESHOLD_ZONES
        )

        high_intensity_minutes = sum(
            session.duration_minutes
            for session in self.sessions
            if session.primary_zone in HIGH_INTENSITY_ZONES
        )

        return {
            "low_intensity": (low_intensity_minutes / total_minutes) * 100,
            "threshold": (threshold_minutes / total_minutes) * 100,
            "high_intensity": (high_intensity_minutes / total_minutes) * 100,
        }


class IntensityDistributionSummary(BaseModel):
    """Summary of intensity distribution across the entire plan."""

    low_intensity_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in Active Recovery + Endurance zones"
    )
    threshold_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in Tempo + Threshold zones"
    )
    high_intensity_percent: float = Field(
        ..., ge=0, le=100, description="Percentage of volume in VO2max + Anaerobic + Sprint zones"
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

    # Adherence tracking (computed from linked activities)
    adherence_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Overall adherence metrics: completion_rate, zone_accuracy, volume_variance"
    )

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

                if session.primary_zone in LOW_INTENSITY_ZONES:
                    total_low_minutes += session.duration_minutes
                elif session.primary_zone in THRESHOLD_ZONES:
                    total_threshold_minutes += session.duration_minutes
                elif session.primary_zone in HIGH_INTENSITY_ZONES:
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

    def calculate_adherence(self) -> Dict[str, float]:
        """
        Calculate plan adherence from linked activities.

        Returns:
            Dictionary with adherence metrics:
            - completion_rate: Percentage of planned sessions completed (0-1)
            - total_planned: Total number of planned sessions
            - total_completed: Number of completed sessions
            - total_partial: Number of partially completed sessions
            - total_missed: Number of missed sessions
        """
        total_sessions = 0
        completed_sessions = 0
        partial_sessions = 0
        missed_sessions = 0

        for week in self.weeks:
            for session in week.sessions:
                total_sessions += 1
                if session.adherence_status == "completed":
                    completed_sessions += 1
                elif session.adherence_status == "partial":
                    partial_sessions += 1
                elif session.adherence_status == "missed":
                    missed_sessions += 1

        completion_rate = completed_sessions / total_sessions if total_sessions > 0 else 0.0

        return {
            "completion_rate": completion_rate,
            "total_planned": total_sessions,
            "total_completed": completed_sessions,
            "total_partial": partial_sessions,
            "total_missed": missed_sessions,
        }
