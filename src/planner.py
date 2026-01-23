"""
Training plan generator with fragility-based adjustments.

This module creates structured multi-week training plans based on:
- Methodology requirements (polarized 80/20 intensity distribution)
- User profile and goals (volume, race timeline, preferences)
- Fragility score (risk-based adjustments to intensity frequency)
"""

from datetime import date
from typing import Any, Dict, List, Tuple

from src.fragility import FragilityCalculator
from src.plan_schemas import (
    HIGH_INTENSITY_ZONES,
    IntensityZone,
    LOW_INTENSITY_ZONES,
    PlanDecision,
    SessionType,
    THRESHOLD_ZONES,
    TrainingPhase,
    TrainingPlan,
    TrainingSession,
    TrainingWeek,
    Weekday,
    WeekType,
    get_zone_display,
)
from src.schemas import MethodologyModelCard, PeriodizationConfig, UserProfile
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

        # 3. Determine load:recovery ratio based on fragility and experience
        load_weeks, recovery_weeks = self._determine_load_recovery_ratio(
            fragility_result.score, user_profile
        )

        # 4. Build mesocycle structure with recovery weeks
        mesocycle_structure = self._build_mesocycle_structure(
            weeks_to_race, load_weeks, recovery_weeks, phases
        )

        # 5. Determine HI session frequency based on fragility
        hi_sessions_per_week = self._determine_hi_frequency(
            fragility_result.score, weeks_to_race, user_profile
        )

        # 6. Generate week-by-week with mesocycle awareness
        weeks = []
        for week_struct in mesocycle_structure:
            week = self._generate_week(
                week_number=week_struct["week_number"],
                phase=week_struct["phase"],
                user_profile=user_profile,
                fragility_score=fragility_result.score,
                hi_sessions_per_week=hi_sessions_per_week,
                phases=phases,
                week_structure=week_struct,
            )
            weeks.append(week)

        # 7. Create plan
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

        # 8. Calculate and store intensity distribution
        plan.intensity_distribution = plan.calculate_intensity_distribution()

        return plan

    def _determine_phases(
        self, weeks_to_race: int, user_profile: UserProfile
    ) -> Dict[str, int]:
        """
        Determine the duration of each training phase from methodology configuration.

        Phases are allocated based on methodology's phase_distribution_config.
        Configuration varies by plan length (short/medium/long).

        Args:
            weeks_to_race: Total weeks until race
            user_profile: User profile with training history

        Returns:
            Dictionary mapping phase names to week counts
        """
        # Get phase percentages from methodology configuration
        phase_config = self._get_phase_percentages(weeks_to_race)

        # Calculate phase weeks based on configured percentages
        base_weeks = max(
            phase_config["min_base_weeks"],
            int(weeks_to_race * phase_config["base_percent"])
        )
        build_weeks = max(
            phase_config["min_build_weeks"],
            int(weeks_to_race * phase_config["build_percent"])
        )
        peak_weeks = max(
            phase_config["min_peak_weeks"],
            int(weeks_to_race * phase_config["peak_percent"])
        )
        taper_weeks = max(
            phase_config["min_taper_weeks"],
            int(weeks_to_race * phase_config["taper_percent"])
        )

        # Adjust for volume consistency using methodology configuration
        volume_consistency = user_profile.current_state.volume_consistency_weeks
        consistency_threshold = self.methodology.phase_distribution_config.volume_consistency_threshold
        extension_weeks = self.methodology.phase_distribution_config.base_extension_weeks

        if volume_consistency < consistency_threshold:
            # Insufficient base, extend base phase
            base_weeks += extension_weeks
            build_weeks = max(1, build_weeks - extension_weeks)

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

    def _get_periodization_config(self) -> PeriodizationConfig:
        """
        Get periodization config from methodology or create default.

        Returns:
            PeriodizationConfig (from methodology or sensible defaults)
        """
        if self.methodology.periodization_config:
            return self.methodology.periodization_config

        # Default configuration if not specified in methodology
        return PeriodizationConfig()

    def _determine_load_recovery_ratio(
        self,
        fragility_score: float,
        user_profile: UserProfile,
    ) -> Tuple[int, int]:
        """
        Determine load:recovery ratio based on fragility and experience.

        Args:
            fragility_score: Calculated F-Score (0.0-1.0)
            user_profile: User profile with training history

        Returns:
            Tuple of (load_weeks, recovery_weeks)
        """
        config = self._get_periodization_config()

        # Check fragility threshold
        high_fragility = fragility_score > config.fragility_threshold

        # Check experience threshold
        years_training = 0.0
        if user_profile.training_history and user_profile.training_history.years_training:
            years_training = user_profile.training_history.years_training
        beginner = years_training < config.experience_threshold_years

        # Select ratio
        if high_fragility or beginner:
            ratio = config.high_fragility_ratio
            if high_fragility and beginner:
                reason = "high fragility AND beginner (<2 years)"
            elif high_fragility:
                reason = f"high fragility (>{config.fragility_threshold})"
            else:
                reason = f"beginner (<{config.experience_threshold_years} years training)"
        else:
            ratio = config.default_ratio
            reason = "experienced athlete with moderate/low fragility"

        # Document decision
        self.plan_decisions.append(
            PlanDecision(
                decision_point="Load:Recovery Ratio Selection",
                input_factors=[
                    f"fragility_score={fragility_score:.2f}",
                    f"years_training={years_training:.1f}",
                    f"fragility_threshold={config.fragility_threshold}",
                    f"experience_threshold={config.experience_threshold_years}",
                ],
                reasoning=f"Selected {ratio.load_weeks}:{ratio.recovery_weeks} ratio due to {reason}. "
                f"Mesocycle length: {ratio.mesocycle_length} weeks. "
                f"Recovery weeks allow adaptation and prevent overtraining.",
                outcome=f"{ratio.load_weeks}:{ratio.recovery_weeks} load:recovery ratio "
                f"({ratio.mesocycle_length}-week mesocycles)",
            )
        )

        return (ratio.load_weeks, ratio.recovery_weeks)

    def _build_mesocycle_structure(
        self,
        total_weeks: int,
        load_weeks: int,
        recovery_weeks: int,
        phases: Dict[str, int],
    ) -> List[Dict[str, Any]]:
        """
        Build the mesocycle structure for the entire plan.

        Args:
            total_weeks: Total plan duration
            load_weeks: Load weeks per mesocycle
            recovery_weeks: Recovery weeks per mesocycle
            phases: Phase duration dictionary

        Returns:
            List of week metadata dicts with:
            - week_number (1-based)
            - week_type (WeekType)
            - mesocycle_number (1-based)
            - mesocycle_week (1-based position within mesocycle)
            - phase (TrainingPhase)
        """
        config = self._get_periodization_config()
        mesocycle_length = load_weeks + recovery_weeks

        structure = []
        mesocycle_num = 1
        week_in_mesocycle = 1

        # Calculate taper start week
        taper_start = phases["base"] + phases["build"] + phases["peak"] + 1

        for week_num in range(1, total_weeks + 1):
            phase = self._get_phase_for_week(week_num, phases)

            # Taper phase uses its own volume reduction - not mesocycle recovery
            if phase == TrainingPhase.TAPER:
                structure.append({
                    "week_number": week_num,
                    "week_type": WeekType.LOAD,  # Taper handles its own reduction
                    "mesocycle_number": None,
                    "mesocycle_week": None,
                    "phase": phase,
                })
                continue

            # Check if this is a recovery week
            is_recovery = (week_in_mesocycle > load_weeks)

            # Option: Skip final mesocycle recovery if next week is taper
            if is_recovery and config.skip_final_mesocycle_recovery:
                if week_num + 1 >= taper_start:
                    is_recovery = False  # Convert to load week

            structure.append({
                "week_number": week_num,
                "week_type": WeekType.RECOVERY if is_recovery else WeekType.LOAD,
                "mesocycle_number": mesocycle_num,
                "mesocycle_week": week_in_mesocycle,
                "phase": phase,
            })

            # Advance mesocycle counter
            week_in_mesocycle += 1
            if week_in_mesocycle > mesocycle_length:
                week_in_mesocycle = 1
                mesocycle_num += 1

        # Document decision
        recovery_count = sum(1 for w in structure if w["week_type"] == WeekType.RECOVERY)
        load_count = sum(1 for w in structure if w["week_type"] == WeekType.LOAD)
        total_mesocycles = max(
            (w.get("mesocycle_number") or 0) for w in structure
        )

        self.plan_decisions.append(
            PlanDecision(
                decision_point="Mesocycle Structure",
                input_factors=[
                    f"total_weeks={total_weeks}",
                    f"mesocycle_length={mesocycle_length}",
                    f"taper_start_week={taper_start}",
                    f"load_weeks_per_cycle={load_weeks}",
                ],
                reasoning=f"Built mesocycle structure with {total_mesocycles} mesocycle(s). "
                f"Recovery weeks strategically placed at end of each mesocycle to allow "
                f"physiological adaptation and prevent cumulative fatigue.",
                outcome=f"{load_count} load weeks, {recovery_count} recovery weeks",
            )
        )

        return structure

    def _calculate_recovery_volume_multiplier(
        self,
        fragility_score: float,
        phase: TrainingPhase,
    ) -> float:
        """
        Calculate volume multiplier for recovery week based on fragility.

        Higher fragility = more aggressive deload (closer to min).

        Args:
            fragility_score: F-Score (0.0-1.0)
            phase: Current training phase

        Returns:
            Volume multiplier (e.g., 0.55 for 55% of normal volume)
        """
        config = self._get_periodization_config()
        rc = config.recovery_week_config

        # Interpolate between min and max based on fragility
        # High fragility (1.0) -> use min multiplier (more rest)
        # Low fragility (0.0) -> use max multiplier (less rest needed)
        base_multiplier = rc.volume_multiplier_max - (
            (rc.volume_multiplier_max - rc.volume_multiplier_min) * fragility_score
        )

        # Apply phase-specific adjustment
        phase_adjustment = config.phase_deload_adjustments.get(phase.value, 0.0)
        final_multiplier = base_multiplier - phase_adjustment

        # Clamp to valid range
        return max(rc.volume_multiplier_min, min(rc.volume_multiplier_max, final_multiplier))

    def _generate_week_notes(
        self,
        week_type: WeekType,
        phase: TrainingPhase,
        volume_multiplier: float,
        week_structure: Dict[str, Any],
    ) -> str:
        """
        Generate contextual notes for the week.

        Args:
            week_type: Whether load or recovery week
            phase: Training phase
            volume_multiplier: Applied volume multiplier
            week_structure: Mesocycle structure info

        Returns:
            Week notes string or None
        """
        config = self._get_periodization_config()

        if week_type == WeekType.RECOVERY:
            volume_percent = int(volume_multiplier * 100)
            return config.recovery_week_config.week_note_template.format(
                volume_percent=volume_percent
            )
        elif phase == TrainingPhase.TAPER:
            return "TAPER WEEK: Prioritize rest and recovery. Maintain intensity but reduce volume significantly."
        elif phase == TrainingPhase.PEAK:
            return "PEAK WEEK: Maximum intensity focus. Ensure adequate recovery between sessions."
        elif week_structure.get("mesocycle_week") == 1:
            mesocycle_num = week_structure.get("mesocycle_number", 1)
            return f"Mesocycle {mesocycle_num} begins. Progressive loading phase - build fitness systematically."

        return None

    def _get_phase_percentages(self, weeks_to_race: int) -> Dict[str, float]:
        """
        Get phase distribution percentages from methodology configuration.

        Args:
            weeks_to_race: Number of weeks until race

        Returns:
            Dict with base_percent, build_percent, peak_percent, taper_percent,
            and minimum weeks for each phase
        """
        config = self.methodology.phase_distribution_config

        # Select configuration based on plan length
        if weeks_to_race <= 6:
            phase_config = config.short_plan_phases
        elif weeks_to_race <= 12:
            phase_config = config.medium_plan_phases
        else:
            phase_config = config.long_plan_phases

        return {
            "base_percent": phase_config.base_percent,
            "build_percent": phase_config.build_percent,
            "peak_percent": phase_config.peak_percent,
            "taper_percent": phase_config.taper_percent,
            "min_base_weeks": phase_config.min_base_weeks,
            "min_build_weeks": phase_config.min_build_weeks,
            "min_peak_weeks": phase_config.min_peak_weeks,
            "min_taper_weeks": phase_config.min_taper_weeks,
        }

    def _get_intensity_targets(self, week_volume_minutes: float) -> tuple[float, float, float]:
        """
        Calculate target minutes for each intensity zone from methodology configuration.

        Args:
            week_volume_minutes: Total weekly training volume in minutes

        Returns:
            Tuple of (low_intensity_minutes, threshold_intensity_minutes, high_intensity_minutes)
        """
        config = self.methodology.intensity_distribution_config

        low_intensity_target = week_volume_minutes * config.low_intensity_target
        threshold_intensity_target = week_volume_minutes * config.threshold_intensity_target
        high_intensity_target = week_volume_minutes * config.high_intensity_target

        return (low_intensity_target, threshold_intensity_target, high_intensity_target)

    def _select_spaced_hi_days(
        self,
        available_days: List[Weekday],
        num_hi_sessions: int,
        min_gap: int = 2,
    ) -> List[Weekday]:
        """
        Select days for high-intensity sessions with minimum recovery spacing.

        Ensures at least min_gap days between hard sessions to allow recovery.

        Args:
            available_days: List of available training days
            num_hi_sessions: Number of HI sessions to place
            min_gap: Minimum days between HI sessions (default 2)

        Returns:
            List of selected days for HI sessions
        """
        if num_hi_sessions == 0 or not available_days:
            return []

        # Map weekdays to numeric indices for spacing calculation
        day_order = {
            Weekday.MONDAY: 0,
            Weekday.TUESDAY: 1,
            Weekday.WEDNESDAY: 2,
            Weekday.THURSDAY: 3,
            Weekday.FRIDAY: 4,
            Weekday.SATURDAY: 5,
            Weekday.SUNDAY: 6,
        }

        # Sort available days by weekday order
        sorted_days = sorted(available_days, key=lambda d: day_order[d])

        if num_hi_sessions == 1:
            # Single HI session: prefer mid-week (Tuesday/Wednesday)
            preferred = [Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY]
            for pref in preferred:
                if pref in sorted_days:
                    return [pref]
            return [sorted_days[0]]

        # Multiple HI sessions: space them out
        selected = []
        last_index = -min_gap  # Allow first selection

        for day in sorted_days:
            if len(selected) >= num_hi_sessions:
                break

            day_index = day_order[day]
            if day_index - last_index >= min_gap:
                selected.append(day)
                last_index = day_index

        # If we couldn't fit all sessions with ideal spacing, reduce gap
        if len(selected) < num_hi_sessions:
            selected = []
            last_index = -1  # Minimum 1 day gap

            for day in sorted_days:
                if len(selected) >= num_hi_sessions:
                    break

                day_index = day_order[day]
                if day_index - last_index >= 1:  # At least 1 day between
                    selected.append(day)
                    last_index = day_index

        # Last resort: just take first N days
        if len(selected) < num_hi_sessions:
            selected = sorted_days[:num_hi_sessions]

        return selected

    def _get_hi_workout_template(
        self,
        session_index: int,
        phase: TrainingPhase,
        hi_sessions_per_week: int,
        week_number: int = 1,
    ) -> Dict[str, Any]:
        """
        Get high-intensity workout template from methodology configuration.

        Selects templates weighted by the methodology's intensity distribution targets
        to ensure proper threshold/VO2max balance, with week-over-week progression.

        Args:
            session_index: Index of HI session (for rotation)
            phase: Current training phase
            hi_sessions_per_week: Total HI sessions per week
            week_number: Week number for progression variety

        Returns:
            Dict with session_type, primary_zone, workout_description
        """
        config = self.methodology.session_type_config
        templates = config.hi_workout_templates

        # Filter templates appropriate for current phase if using phase_specific strategy
        if config.rotation_strategy == "phase_specific":
            phase_templates = [
                t for t in templates if phase.value in t.recommended_phases
            ]
            if phase_templates:
                templates = phase_templates

        # Calculate target number of threshold vs VO2max sessions based on intensity distribution
        intensity_config = self.methodology.intensity_distribution_config
        threshold_target = intensity_config.threshold_intensity_target
        high_target = intensity_config.high_intensity_target

        # If both threshold and high intensity exist, allocate proportionally
        if threshold_target > 0 and high_target > 0:
            total_intensity = threshold_target + high_target
            # Calculate how many sessions should be threshold vs VO2max
            threshold_sessions_target = round((threshold_target / total_intensity) * hi_sessions_per_week)

            # Separate templates by zone (support both old and new zone names)
            threshold_zones = ["zone_3", "threshold", "tempo"]
            hi_zones = ["zone_4", "zone_5", "vo2max", "anaerobic", "sprint"]

            threshold_templates = [t for t in templates if t.primary_zone.lower() in threshold_zones]
            hi_templates = [t for t in templates if t.primary_zone.lower() in hi_zones]

            # Select appropriate template based on session index and targets
            # Use week_number to rotate through templates for variety
            if session_index < threshold_sessions_target and threshold_templates:
                # Use threshold template with week rotation
                template_idx = (session_index + week_number) % len(threshold_templates)
                template = threshold_templates[template_idx]
            elif hi_templates:
                # Use VO2max/anaerobic template with week rotation
                hi_index = session_index - threshold_sessions_target
                template_idx = (hi_index + week_number) % len(hi_templates)
                template = hi_templates[template_idx]
            else:
                # Fallback to any template with rotation
                template = templates[(session_index + week_number) % len(templates)]
        else:
            # Standard round robin if only one intensity type
            if config.rotation_strategy == "random":
                import random
                template = random.choice(templates)
            else:  # round_robin with week rotation for variety
                template = templates[(session_index + week_number) % len(templates)]

        # Apply week-based progression to workout description
        workout_desc = self._apply_workout_progression(
            template.workout_description,
            week_number,
            phase,
        )

        return {
            "session_type": template.session_type,
            "primary_zone": template.primary_zone,
            "workout_description": workout_desc,
            "discipline": template.discipline,
        }

    def _apply_workout_progression(
        self,
        base_description: str,
        week_number: int,
        phase: TrainingPhase,
    ) -> str:
        """
        Apply week-over-week progression to workout description.

        Modifies rep counts and recovery times based on week within phase.

        Args:
            base_description: Original workout description
            week_number: Current week number
            phase: Current training phase

        Returns:
            Modified workout description with progression applied
        """
        import re

        # Only apply progression in build and peak phases
        if phase not in [TrainingPhase.BUILD, TrainingPhase.PEAK]:
            return base_description

        # Calculate progression factor (weeks into build/peak)
        # This creates variety: week 1 = base, week 2 = +1 rep, week 3 = +2 reps
        progression = (week_number - 1) % 3  # Cycles 0, 1, 2

        # Pattern to find rep counts like "6x800m" or "4x10min"
        rep_pattern = r"(\d+)x(\d+)(m|min|sec)"

        def increment_reps(match):
            reps = int(match.group(1))
            distance = match.group(2)
            unit = match.group(3)
            new_reps = reps + progression
            return f"{new_reps}x{distance}{unit}"

        modified = re.sub(rep_pattern, increment_reps, base_description)

        # If progression applied, note it
        if progression > 0 and modified != base_description:
            modified = modified + f" (Week {(week_number - 1) % 3 + 1} progression)"

        return modified

    def _generate_week(
        self,
        week_number: int,
        phase: TrainingPhase,
        user_profile: UserProfile,
        fragility_score: float,
        hi_sessions_per_week: int,
        phases: Dict[str, int],
        week_structure: Dict[str, Any] = None,
    ) -> TrainingWeek:
        """
        Generate a single week of training with mesocycle awareness.

        Args:
            week_number: Week number (1-based)
            phase: Training phase for this week
            user_profile: User profile with preferences and constraints
            fragility_score: Current fragility score
            hi_sessions_per_week: Number of HI sessions to include
            phases: Phase duration dictionary
            week_structure: Mesocycle structure info (week_type, mesocycle_number, etc.)

        Returns:
            TrainingWeek with all sessions
        """
        # Default week structure if not provided (backward compatibility)
        if week_structure is None:
            week_structure = {
                "week_number": week_number,
                "week_type": WeekType.LOAD,
                "mesocycle_number": None,
                "mesocycle_week": None,
                "phase": phase,
            }

        # Get target volume for this week
        base_volume = user_profile.current_state.weekly_volume_hours
        week_type = week_structure["week_type"]
        config = self._get_periodization_config()

        # Determine effective HI sessions based on week type
        if week_type == WeekType.RECOVERY:
            # Recovery weeks: reduced intensity
            effective_hi_sessions = min(
                hi_sessions_per_week,
                config.recovery_week_config.max_hi_sessions
            )
            # Calculate recovery volume multiplier
            volume_multiplier = self._calculate_recovery_volume_multiplier(
                fragility_score, phase
            )
        elif phase == TrainingPhase.TAPER:
            # Taper weeks: reduce volume progressively
            effective_hi_sessions = hi_sessions_per_week
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
        elif phase == TrainingPhase.PEAK:
            # Peak weeks: maintain full volume
            effective_hi_sessions = hi_sessions_per_week
            volume_multiplier = 1.0
        elif phase == TrainingPhase.BUILD:
            # Build weeks: increase volume slightly (5-10%)
            effective_hi_sessions = hi_sessions_per_week
            volume_multiplier = 1.05
        else:
            # Base weeks: standard volume
            effective_hi_sessions = hi_sessions_per_week
            volume_multiplier = 1.0

        week_volume = base_volume * volume_multiplier

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
            hi_sessions_per_week=effective_hi_sessions,
            week_number=week_number,
        )

        # Generate contextual week notes
        week_notes = self._generate_week_notes(
            week_type, phase, volume_multiplier, week_structure
        )

        return TrainingWeek(
            week_number=week_number,
            phase=phase,
            total_volume_hours=week_volume,
            sessions=sessions,
            week_notes=week_notes,
            week_type=week_type,
            mesocycle_number=week_structure.get("mesocycle_number"),
            mesocycle_week=week_structure.get("mesocycle_week"),
            volume_multiplier=volume_multiplier,
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

        Intensity distribution and workout types are determined by methodology configuration.

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

        # Calculate target minutes for intensity distribution from methodology config
        low_intensity_target, threshold_intensity_target, high_intensity_target = (
            self._get_intensity_targets(week_volume_minutes)
        )

        # Determine training days (exclude rest day)
        training_days = [day for day in available_days if day != rest_day]

        # Rotate long workout sport based on week number for variety
        long_workout_sports = [SessionType.BIKE, SessionType.RUN, SessionType.BIKE]
        long_session_type = long_workout_sports[week_number % len(long_workout_sports)]

        # Place long workout on preferred day
        if long_workout_day in training_days:
            # Long aerobic session (30-40% of weekly volume)
            long_duration = int(week_volume_minutes * 0.35)
            zone_display = get_zone_display(long_session_type, IntensityZone.ENDURANCE)
            sessions.append(
                TrainingSession(
                    day=long_workout_day,
                    session_type=long_session_type,
                    primary_zone=IntensityZone.ENDURANCE,
                    duration_minutes=long_duration,
                    description=f"Long aerobic {long_session_type.value} - {long_duration // 60}hr {long_duration % 60}min @ {zone_display}",
                )
            )
            low_intensity_target -= long_duration
            training_days.remove(long_workout_day)

        # Place intensity sessions with recovery spacing
        # Select days with minimum gap between hard sessions
        hi_days = self._select_spaced_hi_days(training_days, hi_sessions_per_week, min_gap=2)

        # Total intensity time = threshold_target + high_target
        total_intensity_target = threshold_intensity_target + high_intensity_target
        intensity_duration_each = int(total_intensity_target / hi_sessions_per_week) if hi_sessions_per_week > 0 else 0

        for i, day in enumerate(hi_days):
            # Get workout template from methodology configuration with progression
            workout_template = self._get_hi_workout_template(i, phase, hi_sessions_per_week, week_number)

            # Map string session_type to SessionType enum
            session_type_map = {
                "run": SessionType.RUN,
                "swim": SessionType.SWIM,
                "bike": SessionType.BIKE,
            }
            session_type = session_type_map.get(
                workout_template["session_type"].lower(),
                SessionType.BIKE
            )

            # Map string primary_zone to new IntensityZone enum
            zone_map = {
                "zone_3": IntensityZone.THRESHOLD,
                "zone_4": IntensityZone.VO2MAX,
                "zone_5": IntensityZone.ANAEROBIC,
                "threshold": IntensityZone.THRESHOLD,
                "tempo": IntensityZone.TEMPO,
                "vo2max": IntensityZone.VO2MAX,
                "anaerobic": IntensityZone.ANAEROBIC,
                "sprint": IntensityZone.SPRINT,
            }
            primary_zone = zone_map.get(
                workout_template["primary_zone"].lower(),
                IntensityZone.VO2MAX
            )

            # Get sport-specific zone display
            zone_display = get_zone_display(session_type, primary_zone)

            # Use descriptive label based on zone
            if primary_zone in THRESHOLD_ZONES:
                intensity_label = "Threshold"
            else:
                intensity_label = "High-intensity"

            sessions.append(
                TrainingSession(
                    day=day,
                    session_type=session_type,
                    primary_zone=primary_zone,
                    duration_minutes=intensity_duration_each,
                    description=f"{intensity_label} {session_type.value} - {zone_display}",
                    workout_details=workout_template["workout_description"],
                )
            )

            # Remove used day from training_days
            if day in training_days:
                training_days.remove(day)

        # Fill remaining days with easy aerobic sessions
        # Ensure minimum sport distribution: prioritize runs in base phase
        remaining_low_intensity = int(low_intensity_target)
        sessions_to_add = min(len(training_days), 3)  # Max 3 additional sessions

        if sessions_to_add > 0:
            duration_each = remaining_low_intensity // sessions_to_add

            # Count existing sessions by sport
            existing_runs = sum(1 for s in sessions if s.session_type == SessionType.RUN)
            existing_bikes = sum(1 for s in sessions if s.session_type == SessionType.BIKE)
            existing_swims = sum(1 for s in sessions if s.session_type == SessionType.SWIM)

            # Target minimums: 2 runs, 2 bikes, 1 swim per week
            min_runs, min_bikes, min_swims = 2, 2, 1

            for i in range(sessions_to_add):
                if not training_days:
                    break

                day = training_days.pop(0)

                # Prioritize sports that haven't met minimums
                if existing_runs < min_runs:
                    session_type = SessionType.RUN
                    existing_runs += 1
                elif existing_bikes < min_bikes:
                    session_type = SessionType.BIKE
                    existing_bikes += 1
                elif existing_swims < min_swims:
                    session_type = SessionType.SWIM
                    existing_swims += 1
                else:
                    # All minimums met, rotate with week offset for variety
                    rotation = [(SessionType.RUN, existing_runs),
                               (SessionType.BIKE, existing_bikes),
                               (SessionType.SWIM, existing_swims)]
                    # Pick sport with fewest sessions
                    rotation.sort(key=lambda x: x[1])
                    session_type = rotation[0][0]
                    if session_type == SessionType.RUN:
                        existing_runs += 1
                    elif session_type == SessionType.BIKE:
                        existing_bikes += 1
                    else:
                        existing_swims += 1

                zone_display = get_zone_display(session_type, IntensityZone.ENDURANCE)
                sessions.append(
                    TrainingSession(
                        day=day,
                        session_type=session_type,
                        primary_zone=IntensityZone.ENDURANCE,
                        duration_minutes=duration_each,
                        description=f"Easy aerobic {session_type.value} - {duration_each}min @ {zone_display}",
                    )
                )

        return sessions
