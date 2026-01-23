import { apiClient } from './client';
import type { UserProfile } from '../types/profile';

// Matches backend AssumptionCheck schema
export interface AssumptionCheck {
  assumption_key: string;
  passed: boolean;
  user_value: any;
  threshold: any;
  reasoning: string;
}

// Matches backend GateViolation schema
export interface GateViolation {
  condition: string;
  threshold: string;
  severity: 'warning' | 'blocking';
  bridge: string;
  assumption_expectation?: string;
  reasoning_justification?: string;
}

// Matches backend ReasoningTrace schema
export interface ReasoningTrace {
  timestamp: string;
  methodology_id: string;
  athlete_id: string;
  checks: AssumptionCheck[];
  safety_gates: GateViolation[];
  result: 'approved' | 'refused' | 'warning';
  fragility_score?: number;
}

// Matches backend ValidationResult schema (nested in response)
export interface ValidationResultData {
  approved: boolean;
  refusal_response?: {
    status: 'refused' | 'warning' | 'approved';
    violations: GateViolation[];
    reasoning_trace_id?: string;
    message?: string;
  };
  reasoning_trace: ReasoningTrace;
  warnings: string[];
}

// Matches backend ValidationResponse schema
export interface ValidationResult {
  approved: boolean;
  reasoning_trace: string[]; // Human-readable reasoning steps
  warnings: string[];
  refusal_message?: string;
  validation_result: ValidationResultData; // Nested structured data
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
