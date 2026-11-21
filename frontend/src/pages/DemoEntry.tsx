import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, api } from '@/lib/api'

export function DemoEntry() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('Opening the demo…')

  useEffect(() => {
    let cancelled = false
    api('/auth/demo', { method: 'POST' })
      .then(async () => {
        await queryClient.invalidateQueries({ queryKey: ['me'] })
        if (!cancelled) navigate('/app')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 404) {
          setMessage('Demo account is not seeded yet. Make a real one and poke around.')
          return
        }
        setMessage('Could not open the demo. Sign up if you want your own board.')
      })
    return () => {
      cancelled = true
    }
  }, [navigate, queryClient])

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5">
      <p className="font-serif text-3xl">{message}</p>
      <Link to="/signup" className="mt-6 text-ember-2">
        Sign up instead
      </Link>
    </div>
  )
}
