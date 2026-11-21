import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { User } from '@/lib/types'

export function useSession() {
  return useQuery({
    queryKey: ['me'],
    queryFn: () => api<User>('/auth/me'),
    retry: false,
    staleTime: 60_000,
  })
}
