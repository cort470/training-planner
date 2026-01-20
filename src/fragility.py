"""
Fragility score calculation module.

Computes user-specific fragility scores based on methodology weights
and user profile deviations from optimal conditions.
"""

from typing import Dict, List
from pydantic import BaseModel, Field

from src.schemas import MethodologyModelCard, UserProfile, StressLevel, HRVTrend


class FragilityResult(BaseModel):
    """Result object for fragility calculation."""

    score: float = Field(..., ge=0.0, le=1.0, description="Final fragility score (0-1)")
    breakdown: Dict[str, float] = Field(
        ..., description="Contribution of each sensitivity factor"
    )
    interpretation: str = Field(..., description="Risk level interpretation")
    recommendations: List[str] = Field(
        default_factory=list, description="Actionable suggestions to reduce fragility"
    )


class FragilityCalculator:
    """
    Computes user-specific fragility scores based on methodology weights.

    Fragility Score = base_fragility + Σ(weight_i × deviation_penalty_i)

    The fragility score quantifies how vulnerable the athlete is to
    overtraining, injury, or insufficient adaptation given their current state.
    """

    def __init__(self, methodology: MethodologyModelCard):
        """
        Initialize calculator with methodology.

        Args:
            methodology: Methodology containing base fragility and calculation weights
        """
        self.methodology = methodology
        self.base_fragility = methodology.risk_profile.fragility_score
        self.weights = methodology.risk_profile.fragility_calculation_weights

    def calculate(self, user_profile: UserProfile) -> FragilityResult:
        """
        Calculate user-specific fragility score.

        Args:
            user_profile: User profile with current state

        Returns:
            FragilityResult with score, breakdown, interpretation, and recommendations
        """
        # Calculate each penalty
        penalties = {
            "sleep_deviation": self._calculate_sleep_deviation_penalty(user_profile),
            "stress_multiplier": self._calculate_stress_multiplier_penalty(
                user_profile
            ),
            "volume_variance": self._calculate_volume_variance_penalty(user_profile),
            "intensity_frequency": self._calculate_intensity_frequency_penalty(
                user_profile
            ),
            "recovery_quality": self._calculate_recovery_quality_penalty(user_profile),
        }

        # Apply weights and sum
        breakdown = {}
        total_penalty = 0.0
        for factor, penalty in penalties.items():
            weight = self.weights.get(factor, 0.0)
            contribution = penalty * weight
            breakdown[factor] = contribution
            total_penalty += contribution

        # Final score (clamped to 0.0-1.0)
        final_score = max(0.0, min(1.0, self.base_fragility + total_penalty))

        # Generate interpretation and recommendations
        interpretation = self._interpret_score(final_score)
        recommendations = self._generate_recommendations(user_profile, penalties)

        return FragilityResult(
            score=final_score,
            breakdown=breakdown,
            interpretation=interpretation,
            recommendations=recommendations,
        )

    def _calculate_sleep_deviation_penalty(self, user_profile: UserProfile) -> float:
        """
        Calculate sleep deviation penalty.

        Logic:
        - Ideal sleep: 8.0 hours
        - If actual < 7.0: Exponential penalty (high fragility)
        - If 7.0-8.0: Linear penalty
        - If > 8.0: No penalty (diminishing returns)

        Args:
            user_profile: User profile with sleep data

        Returns:
            Penalty value (0.0-1.0)
        """
        sleep_hours = user_profile.current_state.sleep_hours
        ideal_sleep = 8.0
        minimum_sleep = 7.0

        if sleep_hours >= ideal_sleep:
            # No penalty for sufficient sleep
            return 0.0
        elif sleep_hours >= minimum_sleep:
            # Linear penalty between minimum and ideal
            return (ideal_sleep - sleep_hours) / ideal_sleep
        else:
            # Exponential penalty for critically low sleep
            # Base penalty + additional exponential component
            base_penalty = (ideal_sleep - minimum_sleep) / ideal_sleep
            additional_penalty = ((minimum_sleep - sleep_hours) / minimum_sleep) ** 2
            return min(1.0, base_penalty + additional_penalty)

    def _calculate_stress_multiplier_penalty(self, user_profile: UserProfile) -> float:
        """
        Calculate stress level penalty.

        Logic:
        - low: 0.0 (no penalty)
        - moderate: 0.3
        - high: 1.0 (maximum penalty)

        Args:
            user_profile: User profile with stress data

        Returns:
            Penalty value (0.0-1.0)
        """
        stress_level = user_profile.current_state.stress_level

        stress_penalties = {
            StressLevel.LOW: 0.0,
            StressLevel.MODERATE: 0.3,
            StressLevel.HIGH: 1.0,
        }

        return stress_penalties.get(stress_level, 0.0)

    def _calculate_volume_variance_penalty(self, user_profile: UserProfile) -> float:
        """
        Calculate volume consistency penalty.

        Logic:
        - Check if weekly_volume_hours within 6-20 hour range
        - Check if volume_consistency_weeks >= 4
        - Penalty for out-of-range or inconsistent volume

        Args:
            user_profile: User profile with volume data

        Returns:
            Penalty value (0.0-1.0)
        """
        volume_hours = user_profile.current_state.weekly_volume_hours
        consistency_weeks = user_profile.current_state.volume_consistency_weeks or 0

        penalty = 0.0

        # Volume range check
        min_volume = 6.0
        max_volume = 20.0

        if volume_hours < min_volume:
            # Penalty for too little volume
            penalty += (min_volume - volume_hours) / min_volume
        elif volume_hours > max_volume:
            # Penalty for excessive volume
            penalty += (volume_hours - max_volume) / max_volume

        # Consistency check
        min_consistency_weeks = 4
        if consistency_weeks < min_consistency_weeks:
            # Penalty for insufficient consistency
            # Full penalty if no consistency, linear reduction up to 4 weeks
            consistency_penalty = (min_consistency_weeks - consistency_weeks) / min_consistency_weeks
            penalty += consistency_penalty * 0.5  # Weight consistency at 50% of volume variance

        return min(1.0, penalty)

    def _calculate_intensity_frequency_penalty(
        self, user_profile: UserProfile
    ) -> float:
        """
        Calculate high-intensity session frequency risk.

        Logic:
        - Based on weeks_to_race and recovery capacity
        - Shorter race timeline → higher intensity → higher fragility
        - HRV trend considered

        Args:
            user_profile: User profile with race and recovery data

        Returns:
            Penalty value (0.0-1.0)
        """
        weeks_to_race = user_profile.goals.weeks_to_race or 12
        hrv_trend = user_profile.current_state.hrv_trend

        penalty = 0.0

        # Timeline pressure penalty
        if weeks_to_race <= 4:
            # Very short timeline = high intensity pressure
            penalty += 0.8
        elif weeks_to_race <= 8:
            # Medium timeline = moderate intensity pressure
            penalty += 0.4
        elif weeks_to_race <= 12:
            # Standard timeline = low intensity pressure
            penalty += 0.2
        else:
            # Long timeline = minimal intensity pressure
            penalty += 0.1

        # HRV trend adjustment
        if hrv_trend == HRVTrend.DECREASING:
            # Decreasing HRV indicates poor recovery - amplify penalty
            penalty *= 1.5
        elif hrv_trend == HRVTrend.INCREASING:
            # Increasing HRV indicates good recovery - reduce penalty
            penalty *= 0.7

        return min(1.0, penalty)

    def _calculate_recovery_quality_penalty(self, user_profile: UserProfile) -> float:
        """
        Calculate recovery quality penalty.

        Logic:
        - HRV trend: decreasing → 1.0, stable → 0.3, increasing → 0.0
        - Recent illness: true → 1.0, false → 0.0
        - Weighted average of recovery indicators

        Args:
            user_profile: User profile with recovery data

        Returns:
            Penalty value (0.0-1.0)
        """
        hrv_trend = user_profile.current_state.hrv_trend
        recent_illness = user_profile.current_state.recent_illness

        # HRV trend penalty
        hrv_penalties = {
            HRVTrend.INCREASING: 0.0,
            HRVTrend.STABLE: 0.3,
            HRVTrend.DECREASING: 1.0,
            HRVTrend.UNKNOWN: 0.5,  # Assume moderate risk if not tracked
        }

        hrv_penalty = hrv_penalties.get(hrv_trend, 0.5)

        # Recent illness penalty
        illness_penalty = 1.0 if recent_illness else 0.0

        # If both HRV is decreasing AND recent illness, compound the penalty
        if hrv_trend == HRVTrend.DECREASING and recent_illness:
            return 1.0

        # Otherwise, weighted average (70% HRV, 30% illness)
        return min(1.0, (hrv_penalty * 0.7 + illness_penalty * 0.3))

    def _interpret_score(self, score: float) -> str:
        """
        Interpret fragility score into risk level.

        Args:
            score: Fragility score (0.0-1.0)

        Returns:
            Risk level interpretation string
        """
        if score < 0.4:
            return "Low Risk"
        elif score < 0.6:
            return "Moderate Risk"
        elif score < 0.8:
            return "High Risk"
        else:
            return "Critical Risk"

    def _generate_recommendations(
        self, user_profile: UserProfile, penalties: Dict[str, float]
    ) -> List[str]:
        """
        Generate actionable recommendations based on penalties.

        Args:
            user_profile: User profile
            penalties: Dictionary of penalty values for each factor

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Sleep recommendations
        if penalties["sleep_deviation"] > 0.2:
            sleep_hours = user_profile.current_state.sleep_hours
            if sleep_hours < 7.0:
                recommendations.append(
                    f"Increase sleep to 7.5+ hours per night (current: {sleep_hours:.1f} hrs). Sleep is critical for recovery and adaptation."
                )
            else:
                recommendations.append(
                    f"Optimize sleep to 8+ hours per night (current: {sleep_hours:.1f} hrs) to reduce fragility."
                )

        # Stress recommendations
        if penalties["stress_multiplier"] > 0.2:
            stress_level = user_profile.current_state.stress_level.value
            recommendations.append(
                f"Manage life stress through relaxation techniques, time management, or workload reduction (current: {stress_level}). High stress impairs recovery."
            )

        # Volume recommendations
        if penalties["volume_variance"] > 0.2:
            volume_hours = user_profile.current_state.weekly_volume_hours
            consistency_weeks = user_profile.current_state.volume_consistency_weeks or 0

            if volume_hours < 6.0:
                recommendations.append(
                    f"Gradually increase training volume to at least 6 hours per week (current: {volume_hours:.1f} hrs)."
                )
            elif volume_hours > 20.0:
                recommendations.append(
                    f"Reduce training volume below 20 hours per week (current: {volume_hours:.1f} hrs) to avoid overtraining."
                )

            if consistency_weeks < 4:
                recommendations.append(
                    f"Maintain consistent volume for at least 4 consecutive weeks (current: {consistency_weeks} weeks) before increasing intensity."
                )

        # Intensity frequency recommendations
        if penalties["intensity_frequency"] > 0.4:
            weeks_to_race = user_profile.goals.weeks_to_race or 12
            if weeks_to_race <= 4:
                recommendations.append(
                    f"Very short timeline to race ({weeks_to_race} weeks). Consider extending preparation period or reducing race expectations to manage intensity pressure."
                )

        # Recovery quality recommendations
        if penalties["recovery_quality"] > 0.4:
            hrv_trend = user_profile.current_state.hrv_trend
            recent_illness = user_profile.current_state.recent_illness

            if recent_illness:
                recommendations.append(
                    "Recent illness detected. Extend recovery period before resuming high-intensity training."
                )

            if hrv_trend == HRVTrend.DECREASING:
                recommendations.append(
                    "HRV trend is decreasing, indicating poor recovery. Add extra rest days and reduce training load until HRV stabilizes."
                )
            elif hrv_trend == HRVTrend.UNKNOWN:
                recommendations.append(
                    "Consider tracking HRV (Heart Rate Variability) to monitor recovery and optimize training load."
                )

        # If no specific recommendations, provide general advice
        if not recommendations:
            recommendations.append(
                "Current fragility is low. Continue maintaining good sleep, managing stress, and monitoring recovery metrics."
            )

        return recommendations
