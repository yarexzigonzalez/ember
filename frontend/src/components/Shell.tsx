import { useQueryClient } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useSession } from '@/lib/session'
import { cn } from '@/lib/utils'

const nav = [
  { to: '/app', label: 'Pipeline' },
  { to: '/app/ghost', label: 'Ghost Radar' },
  { to: '/app/settings', label: 'Settings' },
]

export function Shell({ children }: { children: ReactNode }) {
  const session = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  async function logout() {
    await api('/auth/logout', { method: 'POST' })
    queryClient.clear()
    navigate('/')
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/80 bg-ink/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 md:px-8">
          <Link to="/app" className="font-serif text-2xl tracking-tight">
            Ember
          </Link>
          <nav className="-mx-1 flex flex-1 gap-1 overflow-x-auto text-sm">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  cn(
                    'shrink-0 rounded-full px-3 py-1.5 transition-colors',
                    isActive ? 'bg-raised-2 text-cream' : 'text-tan hover:text-cream',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm text-tan">
            <span className="hidden max-w-48 truncate lg:inline">
              {session.data?.email}
            </span>
            <Button variant="quiet" size="sm" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 md:px-8">{children}</main>
    </div>
  )
}
