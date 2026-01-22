import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Methodology } from '../types';
import type { UserProfile } from '../types/profile';

interface ProfileStore {
  selectedMethodology: Methodology | null;
  userProfile: UserProfile | null;
  validationResult: any | null;
  trainingPlan: any | null;

  setSelectedMethodology: (methodology: Methodology) => void;
  setUserProfile: (profile: UserProfile) => void;
  setValidationResult: (result: any) => void;
  setTrainingPlan: (plan: any) => void;
  clearAll: () => void;
}

export const useProfileStore = create<ProfileStore>()(
  persist(
    (set) => ({
      selectedMethodology: null,
      userProfile: null,
      validationResult: null,
      trainingPlan: null,

      setSelectedMethodology: (methodology) =>
        set({ selectedMethodology: methodology }),

      setUserProfile: (profile) =>
        set({ userProfile: profile }),

      setValidationResult: (result) =>
        set({ validationResult: result }),

      setTrainingPlan: (plan) =>
        set({ trainingPlan: plan }),

      clearAll: () =>
        set({
          selectedMethodology: null,
          userProfile: null,
          validationResult: null,
          trainingPlan: null,
        }),
    }),
    {
      name: 'training-planner-storage',
    }
  )
);
