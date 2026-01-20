"""
Training plan generator with fragility-based adjustments.

This module creates structured multi-week training plans based on:
- Methodology requirements (polarized 80/20 intensity distribution)
- User profile and goals (volume, race timeline, preferences)
- Fragility score (risk-based adjustments to intensity frequency)
"""

from datetime import date
from typing import Dict, List, Tuple

from src.fragility import FragilityCalculator
from src.plan_schemas import (
    IntensityZone,
    PlanDecision,
    SessionType,
    TrainingPhase,
    TrainingPlan,
    TrainingSession,
    TrainingWeek,
    Weekday,
)
from src.schemas import MethodologyModelCard, UserProfile
from src.validator import ValidationResult


class TrainingPlanGenerator:
    """
    Generates structured training plans based on methodology and user profile.

    The generator:
    1. Validates that the user profile has been approved
    2. Calculates fragility score to determine intensity adjustments
    3. Determines training phases (base/build/peak/taper)
    4. Generates week-by-week sessions following 80/20 intensity distribution
    5. Applies fragility-based adjustments (reduces HI frequency if needed)
    6. Documents all decisions for reasoning trace
    """

    def __init__(
        self,
        methodology: MethodologyModelCard,
        validation_result: ValidationResult,
    ):
        """
        Initialize the plan generator.

        Args:
            methodology: The methodology model card with intensity distribution rules
            validation_result: Validation result (must be approved)

        Raises:
            ValueError: If validation was not approved
        """
        if not validation_result.approved:
            raise ValueError(
                "Cannot generate plan for refused validation. "
                "Validation result must be 'approved' or 'approved_with_warnings'."
            )

        self.methodology = methodology
        self.validation_result = validation_result
        self.plan_decisions: List[PlanDecision] = []

    def generate(self, user_profile: UserProfile) -> TrainingPlan:
        """
        Generate a complete training plan for the user.

        Args:
            user_profile: User profile with goals, constraints, preferences

        Returns:
            TrainingPlan with all weeks and sessions generated

        Raises:
            ValueError: If user profile is missing required fields
        """
        # 1. Calculate fragility score
        calculator = FragilityCalculator(self.methodology)
        fragility_result = calculator.calculate(user_profile)

        # 2. Determine plan duration and phases
        weeks_to_race = user_profile.goals.weeks_to_race or 12
        phases = self._determine_phases(weeks_to_race, user_profile)

        # 3. Determine HI session frequency based on fragility
        hi_sessions_per_week = self._determine_hi_frequency(
            fragility_result.score, weeks_to_race, user_profile
        )

        # 4. Generate week-by-week
        weeks = []
        for week_num in range(1, weeks_to_race + 1):
            phase = self._get_phase_for_week(week_num, phases)
            week = self._generate_week(
                week_number=week_num,
                phase=phase,
                user_profile=user_profile,
                fragility_score=fragility_result.score,
                hi_sessions_per_week=hi_sessions_per_week,
                phases=phases,
            )
            weeks.append(week)

        # 5. Create plan
        plan = TrainingPlan(
            athlete_id=user_profile.athlete_id,
            methodology_id=self.methodology.id,
            plan_start_date=date.today(),
            plan_duration_weeks=weeks_to_race,
            race_date=user_profile.goals.race_date,
            race_distance=user_profile.goals.race_distance.value
            if user_profile.goals.race_distance
            else None,
            weeks=weeks,
            fragility_score=fragility_result.score,
            plan_decisions=self.plan_decisions,
            assumptions_used=user_profile.model_dump(),
        )

        # 6. Calculate and store intensity distribution
        plan.intensity_distribution = plan.calculate_intensity_distribution()

        return plan

    def _determine_phases(
        self, weeks_to_race: int, user_profile: UserProfile
    ) -> Dict[str, int]:
        """
        Determine the duration of each training phase.

        Phases are allocated based on timeline:
        - 4-6 weeks: 40% base, 30% build, 10% peak, 20% taper
        - 8-12 weeks: 30% base, 45% build, 15% peak, 10% taper
        - 16+ weeks: 25% base, 50% build, 15% peak, 10% taper

        Args:
            weeks_to_race: Total weeks until race
            user_profile: User profile with training history

        Returns:
            Dictionary mapping phase names to week counts
        """
        if weeks_to_race <= 6:
            # Short timeline: focus on maintaining fitness with controlled intensity
            base_weeks = max(2, int(weeks_to_race * 0.4))
            build_weeks = max(1, int(weeks_to_race * 0.3))
            peak_weeks = max(1, int(weeks_to_race * 0.1))
            taper_weeks = max(1, int(weeks_to_race * 0.2))
        elif weeks_to_race <= 12:
            # Standard timeline: balanced progression
            base_weeks = max(3, int(weeks_to_race * 0.3))
            build_weeks = max(4, int(weeks_to_race * 0.45))
            peak_weeks = max(2, int(weeks_to_race * 0.15))
            taper_weeks = max(1, int(weeks_to_race * 0.1))
        else:
            # Long timeline: extended base and build
            base_weeks = max(4, int(weeks_to_race * 0.25))
            build_weeks = max(8, int(weeks_to_race * 0.50))
            peak_weeks = max(2, int(weeks_to_race * 0.15))
            taper_weeks = max(2, int(weeks_to_race * 0.10))

        # Adjust for volume consistency
        volume_consistency = user_profile.current_state.volume_consistency_weeks
        if volume_consistency < 4:
            # Insufficient base, extend base phase by 1-2 weeks
            base_weeks += 2
            build_weeks = max(1, build_weeks - 2)

        # Ensure total matches weeks_to_race
        total_assigned = base_weeks + build_weeks + peak_weeks + taper_weeks
        if total_assigned != weeks_to_race:
            # Adjust build phase to match
            build_weeks += weeks_to_race - total_assigned

        phases = {
            "base": base_weeks,
            "build": build_weeks,
            "peak": peak_weeks,
            "taper": taper_weeks,
        }

        # Document decision
        self.plan_decisions.append(
            PlanDecision(
                decision_point="Training Phase Distribution",
                input_factors=[
                    f"weeks_to_race={weeks_to_race}",
                    f"volume_consistency_weeks={volume_consistency}",
                ],
                reasoning=f"Allocated {weeks_to_race} weeks across phases based on timeline. "
                + (
                    "Extended base phase due to low volume consistency (<4 weeks)."
                    if volume_consistency < 4
                    else "Standard phase distribution for well-established base."
                ),
                outcome=f"{base_weeks}wk base, {build_weeks}wk build, {peak_weeks}wk peak, {taper_weeks}wk taper",
            )
        )

        return phases

    def _get_phase_for_week(
        self, week_number: int, phases: Dict[str, int]
    ) -> TrainingPhase:
        """
        Determine which phase a specific week belongs to.

        Args:
            week_number: Week number (1-based)
            phases: Dictionary of phase durations

        Returns:
            TrainingPhase enum value
        """
        base_end = phases["base"]
        build_end = base_end + phases["build"]
        peak_end = build_end + phases["peak"]

        if week_number <= base_end:
            return TrainingPhase.BASE
        elif week_number <= build_end:
            return TrainingPhase.BUILD
        elif week_number <= peak_end:
            return TrainingPhase.PEAK
        else:
            return TrainingPhase.TAPER

    def _determine_hi_frequency(
        self,
        fragility_score: float,
        weeks_to_race: int,
        user_profile: UserProfile,
    ) -> int:
        """
        Determine how many high-intensity sessions per week based on fragility.

        Standard (low fragility): 3 HI sessions/week
        Moderate fragility (0.4-0.6): 2 HI sessions/week
        High fragility (>0.6): 1 HI session/week

        Args:
            fragility_score: F-Score (0.0-1.0)
            weeks_to_race: Timeline to race
            user_profile: User profile

        Returns:
            Number of HI sessions per week (1-3)
        """
        if fragility_score < 0.4:
            hi_frequency = 3
            risk_level = "low"
        elif fragility_score < 0.6:
            hi_frequency = 2
            risk_level = "moderate"
        else:
            hi_frequency = 1
            risk_level = "high"

        # Document decision
        self.plan_decisions.append(
            PlanDecision(
                decision_point="High-Intensity Session Frequency",
                input_factors=[
                    f"fragility_score={fragility_score:.2f}",
                    f"weeks_to_race={weeks_to_race}",
                ],
                reasoning=f"F-Score of {fragility_score:.2f} indicates {risk_level} fragility. "
                + (
                    "Can safely program standard 3 HI sessions per week."
                    if hi_frequency == 3
                    else f"Reducing HI frequency to {hi_frequency}/week to preserve recovery capacity and minimize injury risk."
                ),
                outcome=f"{hi_frequency} high-intensity sessions per week",
            )
        )

        return hi_frequency

    def _generate_week(
        self,
        week_number: int,
        phase: TrainingPhase,
        user_profile: UserProfile,
        fragility_score: float,
        hi_sessions_per_week: int,
        phases: Dict[str, int],
    ) -> TrainingWeek:
        """
        Generate a single week of training.

        Args:
            week_number: Week number (1-based)
            phase: Training phase for this week
            user_profile: User profile with preferences and constraints
            fragility_score: Current fragility score
            hi_sessions_per_week: Number of HI sessions to include
            phases: Phase duration dictionary

        Returns:
            TrainingWeek with all sessions
        """
        # Get target volume for this week
        base_volume = user_profile.current_state.weekly_volume_hours

        # Apply phase-based volume adjustments
        if phase == TrainingPhase.TAPER:
            # Taper weeks: reduce volume progressively
            taper_start_week = (
                phases["base"] + phases["build"] + phases["peak"] + 1
            )
            weeks_into_taper = week_number - taper_start_week + 1
            total_taper_weeks = phases["taper"]

            if weeks_into_taper == total_taper_weeks:
                # Final week: 40% volume
                volume_multiplier = 0.4
            elif weeks_into_taper == total_taper_weeks - 1:
                # Second-to-last week: 60% volume
                volume_multiplier = 0.6
            else:
                # Earlier taper: 70% volume
                volume_multiplier = 0.7

            week_volume = base_volume * volume_multiplier
        elif phase == TrainingPhase.PEAK:
            # Peak weeks: maintain full volume
            week_volume = base_volume * 1.0
        elif phase == TrainingPhase.BUILD:
            # Build weeks: increase volume slightly (5-10%)
            week_volume = base_volume * 1.05
        else:
            # Base weeks: standard volume
            week_volume = base_volume

        # Generate sessions for available days
        num_training_days = user_profile.constraints.available_training_days
        rest_day = user_profile.preferences.rest_day
        long_workout_day = user_profile.preferences.long_workout_day

        # Convert training days count + rest day to actual list of Weekday values
        available_days = self._get_available_days(num_training_days, rest_day)

        # Create session schedule
        sessions = self._create_session_schedule(
            available_days=available_days,
            rest_day=rest_day,
            long_workout_day=long_workout_day,
            week_volume_hours=week_volume,
            phase=phase,
            hi_sessions_per_week=hi_sessions_per_week,
            week_number=week_number,
        )

        # Add week notes if needed
        week_notes = None
        if phase == TrainingPhase.TAPER:
            week_notes = "Taper week: prioritize rest and recovery. Maintain intensity but reduce volume."
        elif phase == TrainingPhase.PEAK:
            week_notes = "Peak week: maximum intensity. Ensure adequate recovery between sessions."

        return TrainingWeek(
            week_number=week_number,
            phase=phase,
            total_volume_hours=week_volume,
            sessions=sessions,
            week_notes=week_notes,
        )

    def _get_available_days(
        self, num_training_days: int, rest_day: Weekday
    ) -> List[Weekday]:
        """
        Convert number of training days and rest day to list of available Weekday values.

        Args:
            num_training_days: Number of training days per week (1-7)
            rest_day: Preferred rest day

        Returns:
            List of Weekday enums representing available training days
        """
        all_days = [
            Weekday.MONDAY,
            Weekday.TUESDAY,
            Weekday.WEDNESDAY,
            Weekday.THURSDAY,
            Weekday.FRIDAY,
            Weekday.SATURDAY,
            Weekday.SUNDAY,
        ]

        # If rest day specified, remove it first
        if rest_day:
            available = [day for day in all_days if day != rest_day]
        else:
            available = all_days.copy()

        # Return the first num_training_days
        return available[:num_training_days]

    def _create_session_schedule(
        self,
        available_days: List[Weekday],
        rest_day: Weekday,
        long_workout_day: Weekday,
        week_volume_hours: float,
        phase: TrainingPhase,
        hi_sessions_per_week: int,
        week_number: int,
    ) -> List[TrainingSession]:
        """
        Create the session schedule for a week.

        Follows 80/20 polarized intensity distribution:
        - 80% of volume in Zone 1-2 (easy aerobic)
        - 20% of volume in Zone 4-5 (high intensity)
        - Zone 3 (tempo) minimized

        Args:
            available_days: Days available for training
            rest_day: Preferred rest day
            long_workout_day: Preferred day for long workout
            week_volume_hours: Total volume for the week
            phase: Training phase
            hi_sessions_per_week: Number of HI sessions
            week_number: Week number (for variety)

        Returns:
            List of TrainingSession objects
        """
        sessions = []
        week_volume_minutes = week_volume_hours * 60

        # Calculate target minutes for intensity distribution (80/20)
        low_intensity_target = week_volume_minutes * 0.80
        high_intensity_target = week_volume_minutes * 0.20

        # Determine training days (exclude rest day)
        training_days = [day for day in available_days if day != rest_day]

        # Place long workout on preferred day
        if long_workout_day in training_days:
            # Long aerobic session (30-40% of weekly volume)
            long_duration = int(week_volume_minutes * 0.35)
            sessions.append(
                TrainingSession(
                    day=long_workout_day,
                    session_type=SessionType.BIKE,
                    primary_zone=IntensityZone.ZONE_2,
                    duration_minutes=long_duration,
                    description=f"Long aerobic ride - {long_duration // 60}hr {long_duration % 60}min @ Z2",
                )
            )
            low_intensity_target -= long_duration
            training_days.remove(long_workout_day)

        # Place HI sessions on separate days
        hi_duration_each = int(high_intensity_target / hi_sessions_per_week)

        for i in range(hi_sessions_per_week):
            if not training_days:
                break

            day = training_days.pop(0)

            # Alternate between different HI session types
            if i % 3 == 0:
                session_type = SessionType.RUN
                workout_details = "VO2max intervals: 6×800m @ Z4 with 2min recovery"
            elif i % 3 == 1:
                session_type = SessionType.SWIM
                workout_details = "Threshold intervals: 8×100m @ Z4 with 90sec rest"
            else:
                session_type = SessionType.BIKE
                workout_details = "Sweet spot intervals: 4×10min @ Z4 with 3min recovery"

            sessions.append(
                TrainingSession(
                    day=day,
                    session_type=session_type,
                    primary_zone=IntensityZone.ZONE_4,
                    duration_minutes=hi_duration_each,
                    description=f"High-intensity {session_type.value} session",
                    workout_details=workout_details,
                )
            )

        # Fill remaining days with easy aerobic sessions
        remaining_low_intensity = int(low_intensity_target)
        sessions_to_add = min(len(training_days), 3)  # Max 3 additional sessions

        if sessions_to_add > 0:
            duration_each = remaining_low_intensity // sessions_to_add

            for i in range(sessions_to_add):
                if not training_days:
                    break

                day = training_days.pop(0)

                # Rotate session types
                if i % 3 == 0:
                    session_type = SessionType.RUN
                elif i % 3 == 1:
                    session_type = SessionType.SWIM
                else:
                    session_type = SessionType.BIKE

                sessions.append(
                    TrainingSession(
                        day=day,
                        session_type=session_type,
                        primary_zone=IntensityZone.ZONE_2,
                        duration_minutes=duration_each,
                        description=f"Easy aerobic {session_type.value} - {duration_each}min @ Z2",
                    )
                )

        return sessions
