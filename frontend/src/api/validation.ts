import { apiClient } from './client';
import type { UserProfile } from '../types/profile';

export interface ValidationResult {
  approved: boolean;
  reasoning_trace: {
    methodology_id: string;
    validation_timestamp: string;
    assumptions_checked: Array<{
      assumption_key: string;
      passed: boolean;
      user_value: any;
      threshold: any;
      reasoning: string;
    }>;
    safety_gates_evaluated: Array<{
      condition: string;
      threshold: string;
      severity: 'warning' | 'blocking';
      passed: boolean;
      reasoning: string;
    }>;
    decision: 'approved' | 'blocked' | 'approved_with_warnings';
    warnings: string[];
    blocking_violations: string[];
  };
  fragility_score?: number;
  fragility_interpretation?: string;
}

export const validationApi = {
  validate: async (userProfile: UserProfile, methodologyId: string): Promise<ValidationResult> => {
    const response = await apiClient.post('/api/validate', {
      user_profile: userProfile,
      methodology_id: methodologyId,
    });
    return response.data;
  },
};
