import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, api } from '@/lib/api'
import type { User } from '@/lib/types'

// Render's free tier naps after 15 idle minutes, so the first request can take
// a while (and sometimes 502s while it boots). Keep the visitor in the loop.
const RETRIES = 4

export function DemoEntry() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [slow, setSlow] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const slowTimer = setTimeout(() => setSlow(true), 2500)

    async function enter() {
      for (let attempt = 0; attempt <= RETRIES; attempt++) {
        try {
          const user = await api<User>('/auth/demo', { method: 'POST' })
          if (cancelled) return
          queryClient.setQueryData(['me'], user)
          navigate('/app', { replace: true })
          return
        } catch (error) {
          if (cancelled) return
          const status = error instanceof ApiError ? error.status : 0
          if (status === 404) return setFailed("Demo account isn't seeded yet.")
          if (status === 429)
            return setFailed('Too many demo opens from here. Give it a few minutes.')
          // network error / 502 / 503 = server still waking up, try again
          if (attempt === RETRIES)
            return setFailed("Server didn't wake up. Try again in a minute.")
          await new Promise((resolve) => setTimeout(resolve, 2000 * (attempt + 1)))
        }
      }
    }
    enter()
    return () => {
      cancelled = true
      clearTimeout(slowTimer)
    }
  }, [navigate, queryClient])

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5">
      {failed ? (
        <>
          <p className="font-serif text-3xl">{failed}</p>
          <Link to="/signup" className="mt-6 text-ember-2">
            Make your own account instead
          </Link>
        </>
      ) : (
        <>
          <motion.div
            className="size-3 rounded-full bg-ember"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          />
          <p className="mt-5 font-serif text-3xl">Opening the demo…</p>
          {slow && (
            <p className="mt-3 text-tan">
              Server's on a free tier and naps when nobody's around. Waking it up, usually
              takes under a minute.
            </p>
          )}
        </>
      )}
    </div>
  )
}
