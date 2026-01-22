import { apiClient } from './client';

export interface Methodology {
  id: string;
  name: string;
  description: string;
  fragility_score: number;
  intensity_distribution: string;
}

interface MethodologiesResponse {
  methodologies: Methodology[];
  count: number;
}

export const methodologiesApi = {
  getAll: async (): Promise<Methodology[]> => {
    const response = await apiClient.get<MethodologiesResponse>('/api/methodologies');
    return response.data.methodologies;
  },

  getById: async (id: string): Promise<any> => {
    const response = await apiClient.get(`/api/methodologies/${id}`);
    return response.data;
  },
};
