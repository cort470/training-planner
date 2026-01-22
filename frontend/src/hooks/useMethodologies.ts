import { useQuery } from '@tanstack/react-query';
import { methodologiesApi } from '../api/methodologies';

export function useMethodologies() {
  return useQuery({
    queryKey: ['methodologies'],
    queryFn: methodologiesApi.getAll,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours (methodologies rarely change)
  });
}
