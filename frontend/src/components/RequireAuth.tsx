import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useSession } from '@/lib/session'

export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession()
  if (session.isLoading) {
    return <p className="p-10 text-tan">Checking the session…</p>
  }
  if (!session.data) return <Navigate to="/login" replace />
  return children
}
