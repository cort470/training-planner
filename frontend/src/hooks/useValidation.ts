import { useMutation } from '@tanstack/react-query';
import { validationApi, type ValidationResult } from '../api/validation';
import type { UserProfile } from '../types/profile';

interface ValidateParams {
  userProfile: UserProfile;
  methodologyId: string;
}

export function useValidation() {
  return useMutation<ValidationResult, Error, ValidateParams>({
    mutationFn: ({ userProfile, methodologyId }) =>
      validationApi.validate(userProfile, methodologyId),
  });
}
