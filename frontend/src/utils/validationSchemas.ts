import { z } from 'zod';

export const profileFormSchema = z.object({
  // Basic Info
  athlete_id: z.string()
    .min(3, 'Athlete ID must be at least 3 characters')
    .max(50, 'Athlete ID must be less than 50 characters')
    .regex(/^[a-zA-Z0-9_-]+$/, 'Only letters, numbers, hyphens, and underscores allowed'),

  // Current State
  sleep_hours: z.number()
    .min(4, 'Sleep hours must be at least 4')
    .max(12, 'Sleep hours must be less than 12'),

  injury_status: z.boolean(),

  injury_details: z.string().optional(),

  stress_level: z.enum(['low', 'moderate', 'high']),

  stress_details: z.string().optional(),

  weekly_volume_hours: z.number()
    .min(0, 'Weekly volume must be at least 0')
    .max(40, 'Weekly volume must be less than 40'),

  volume_consistency_weeks: z.number()
    .min(0, 'Must be at least 0')
    .max(52, 'Must be less than 52')
    .optional(),

  hrv_trend: z.enum(['increasing', 'stable', 'decreasing', 'unknown']).default('unknown'),

  recent_illness: z.boolean().default(false),

  menstrual_cycle_phase: z.enum(['follicular', 'ovulation', 'luteal', 'menstruation', 'not_applicable']).default('not_applicable'),

  // Training History
  years_training: z.number()
    .min(0, 'Years training must be at least 0')
    .max(50, 'Years training must be less than 50')
    .optional(),

  // Goals
  primary_goal: z.enum(['race_performance', 'base_building', 'weight_loss', 'general_fitness', 'injury_prevention']),

  race_date: z.string().optional(),

  race_distance: z.enum(['sprint', 'olympic', 'half_ironman', 'ironman', '70.3', 'other']).optional(),

  weeks_to_race: z.number()
    .min(1, 'Must be at least 1 week')
    .max(52, 'Must be less than 52 weeks')
    .optional(),

  priority_level: z.enum(['A', 'B', 'C']).default('B'),

  // Constraints
  available_training_days: z.number()
    .min(1, 'Must be at least 1 day')
    .max(7, 'Must be at most 7 days')
    .default(6),

  max_session_duration_hours: z.number()
    .min(0.5, 'Must be at least 0.5 hours')
    .max(8, 'Must be less than 8 hours')
    .default(2.5),

  // Preferences
  long_workout_day: z.enum(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']).optional(),

  rest_day: z.enum(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']).optional(),
}).refine((data) => {
  // If primary_goal is race_performance, race_date and race_distance should be provided
  if (data.primary_goal === 'race_performance') {
    return !!data.race_date && !!data.race_distance;
  }
  return true;
}, {
  message: 'Race date and distance are required when goal is race performance',
  path: ['race_date'],
}).refine((data) => {
  // If injury_status is true, injury_details should be provided
  if (data.injury_status) {
    return !!data.injury_details && data.injury_details.length > 0;
  }
  return true;
}, {
  message: 'Please provide injury details',
  path: ['injury_details'],
});

export type ProfileFormData = z.infer<typeof profileFormSchema>;
