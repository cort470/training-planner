export type StressLevel = 'low' | 'moderate' | 'high';
export type HRVTrend = 'increasing' | 'stable' | 'decreasing' | 'unknown';
export type MenstrualPhase = 'follicular' | 'ovulation' | 'luteal' | 'menstruation' | 'not_applicable';
export type PrimaryGoal = 'race_performance' | 'base_building' | 'weight_loss' | 'general_fitness' | 'injury_prevention';
export type RaceDistance = 'sprint' | 'olympic' | 'half_ironman' | 'ironman' | '70.3' | 'other';
export type RacePriority = 'A' | 'B' | 'C';
export type Weekday = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';
export type IntensityDistribution = 'polarized' | 'pyramidal' | 'threshold' | 'flexible';

export interface CurrentState {
  sleep_hours: number;
  sleep_consistency?: number;
  injury_status: boolean;
  injury_details?: string;
  stress_level: StressLevel;
  stress_details?: string;
  weekly_volume_hours: number;
  volume_consistency_weeks?: number;
  resting_heart_rate?: number;
  hrv_trend: HRVTrend;
  recent_illness: boolean;
  menstrual_cycle_phase: MenstrualPhase;
}

export interface TrainingHistory {
  years_training?: number;
}

export interface Goals {
  primary_goal: PrimaryGoal;
  race_date?: string;
  race_distance?: RaceDistance;
  goal_finish_time?: string;
  weeks_to_race?: number;
  priority_level: RacePriority;
}

export interface Constraints {
  available_training_days: number;
  max_session_duration_hours: number;
}

export interface Preferences {
  preferred_intensity_distribution?: IntensityDistribution;
  long_workout_day?: Weekday;
  rest_day?: Weekday;
}

export interface UserProfile {
  athlete_id: string;
  profile_date: string;
  current_state: CurrentState;
  training_history?: TrainingHistory;
  goals: Goals;
  constraints?: Constraints;
  preferences?: Preferences;
}
