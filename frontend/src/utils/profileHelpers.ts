import type { ProfileFormData } from './validationSchemas';
import type { UserProfile } from '../types/profile';

export function formDataToUserProfile(formData: ProfileFormData): UserProfile {
  const today = new Date().toISOString().split('T')[0];

  return {
    athlete_id: formData.athlete_id,
    profile_date: today,
    current_state: {
      sleep_hours: formData.sleep_hours,
      injury_status: formData.injury_status,
      injury_details: formData.injury_details,
      stress_level: formData.stress_level,
      stress_details: formData.stress_details,
      weekly_volume_hours: formData.weekly_volume_hours,
      volume_consistency_weeks: formData.volume_consistency_weeks,
      hrv_trend: formData.hrv_trend,
      recent_illness: formData.recent_illness,
      menstrual_cycle_phase: formData.menstrual_cycle_phase,
    },
    training_history: formData.years_training
      ? { years_training: formData.years_training }
      : undefined,
    goals: {
      primary_goal: formData.primary_goal,
      race_date: formData.race_date,
      race_distance: formData.race_distance,
      weeks_to_race: formData.weeks_to_race,
      priority_level: formData.priority_level,
    },
    constraints: {
      available_training_days: formData.available_training_days,
      max_session_duration_hours: formData.max_session_duration_hours,
    },
    preferences: {
      long_workout_day: formData.long_workout_day,
      rest_day: formData.rest_day,
    },
  };
}

export function calculateWeeksToRace(raceDate: string): number {
  const today = new Date();
  const race = new Date(raceDate);
  const diffTime = race.getTime() - today.getTime();
  const diffWeeks = Math.ceil(diffTime / (1000 * 60 * 60 * 24 * 7));
  return Math.max(1, diffWeeks);
}
