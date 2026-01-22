import { apiClient } from './client';
import type { UserProfile } from '../types/profile';

export interface TrainingSession {
  day_of_week: string;
  description: string;
  duration_minutes: number;
  primary_zone: string;
  session_type: string;
  workout_details?: any;
}

export interface TrainingWeek {
  week_number: number;
  phase: string;
  weekly_volume_minutes: number;
  sessions: TrainingSession[];
}

export interface TrainingPlan {
  plan_id: string;
  athlete_id: string;
  methodology_id: string;
  created_at: string;
  total_weeks: number;
  race_date?: string;
  weeks: TrainingWeek[];
}

export interface PlanGenerationResult {
  plan: TrainingPlan;
  validation_result: any;
  fragility_result: any;
}

export const plansApi = {
  generate: async (userProfile: UserProfile, methodologyId: string): Promise<PlanGenerationResult> => {
    const response = await apiClient.post('/api/plans', {
      user_profile: userProfile,
      methodology_id: methodologyId,
    });
    return response.data;
  },
};
