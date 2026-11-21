import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import { browserTimezone } from '@/lib/dates'

export function AuthForm({ mode }: { mode: 'login' | 'signup' }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (mode === 'signup') {
        await api('/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            email,
            password,
            display_name: displayName || null,
            timezone: browserTimezone(),
          }),
        })
      }
      await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/app')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in')
    } finally {
      setBusy(false)
    }
  }

  const signup = mode === 'signup'

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5">
      <Link to="/" className="mb-8 font-serif text-2xl">
        Ember
      </Link>
      <h1 className="font-serif text-4xl">{signup ? 'Make an account' : 'Welcome back'}</h1>
      <p className="mt-2 text-tan">
        {signup
          ? 'Email and a password. No third-party login.'
          : 'Pick up the search where you left it.'}
      </p>
      <form onSubmit={onSubmit} className="mt-8 grid gap-4">
        {signup && (
          <Field label="Name">
            <Input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </Field>
        )}
        <Field label="Email">
          <Input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </Field>
        <Field label="Password">
          <Input
            type="password"
            required
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={signup ? 'new-password' : 'current-password'}
          />
        </Field>
        {error && <p className="text-sm text-rose">{error}</p>}
        <Button type="submit" disabled={busy}>
          {busy ? 'Working…' : signup ? 'Sign up' : 'Log in'}
        </Button>
      </form>
      <p className="mt-6 text-sm text-tan">
        {signup ? (
          <>
            Already have one?{' '}
            <Link to="/login" className="text-cream underline">
              Log in
            </Link>
          </>
        ) : (
          <>
            New here?{' '}
            <Link to="/signup" className="text-cream underline">
              Sign up
            </Link>
          </>
        )}
      </p>
    </div>
  )
}
