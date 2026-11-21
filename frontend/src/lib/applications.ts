import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { Application, ApplicationList, Status } from '@/lib/types'

const ALL_KEY = ['applications', 'all'] as const

// Anything that reads application rows. Bump all of it after a write.
export function refreshPipelineData(queryClient: QueryClient) {
  for (const key of ['applications', 'sprint', 'ghost', 'pulse']) {
    queryClient.invalidateQueries({ queryKey: [key] })
  }
}

async function fetchAll(): Promise<Application[]> {
  // Board wants everything. Walk the pages; most people have a few hundred rows tops.
  const rows: Application[] = []
  for (let page = 1; page < 200; page++) {
    const batch = await api<ApplicationList>(`/applications?page=${page}&page_size=100`)
    rows.push(...batch.items)
    if (rows.length >= batch.total || batch.items.length === 0) break
  }
  return rows
}

export function useAllApplications() {
  return useQuery({ queryKey: ALL_KEY, queryFn: fetchAll })
}

export type ListParams = {
  q?: string
  status?: Status | ''
  source?: string
  sort?: 'updated_at' | 'company' | 'role' | 'status' | 'applied_at'
  direction?: 'asc' | 'desc'
}

export function listQueryString(params: ListParams, page: number, pageSize: number) {
  const search = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, String(value))
  }
  return search.toString()
}

export function useMoveApplication() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: Status }) =>
      api<Application>(`/applications/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
    // Move the card right away; snap it back if the server says no.
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ALL_KEY })
      const previous = queryClient.getQueryData<Application[]>(ALL_KEY)
      queryClient.setQueryData<Application[]>(ALL_KEY, (rows) =>
        rows?.map((row) => (row.id === id ? { ...row, status } : row)),
      )
      return { previous }
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(ALL_KEY, context.previous)
    },
    onSettled: () => refreshPipelineData(queryClient),
  })
}
