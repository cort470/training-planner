import { useMutation } from '@tanstack/react-query';
import { plansApi, type PlanGenerationResult } from '../api/plans';
import type { UserProfile } from '../types/profile';

interface GeneratePlanParams {
  userProfile: UserProfile;
  methodologyId: string;
}

export function usePlanGeneration() {
  return useMutation<PlanGenerationResult, Error, GeneratePlanParams>({
    mutationFn: ({ userProfile, methodologyId }) =>
      plansApi.generate(userProfile, methodologyId),
  });
}
