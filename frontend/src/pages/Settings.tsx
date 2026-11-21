import { useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Field, Input, Select } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import { refreshPipelineData } from '@/lib/applications'
import { browserTimezone } from '@/lib/dates'
import { useSession } from '@/lib/session'
import type { User } from '@/lib/types'

function allTimezones(current: string): string[] {
  try {
    const zones = Intl.supportedValuesOf('timeZone')
    return zones.includes(current) ? zones : [current, ...zones]
  } catch {
    return [current]
  }
}

export function Settings() {
  const session = useSession()
  if (!session.data) return null
  return <SettingsForm user={session.data} />
}

function SettingsForm({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(user.display_name ?? '')
  const [timezone, setTimezone] = useState(user.timezone)
  const [goal, setGoal] = useState(user.weekly_goal)
  const [ghostDays, setGhostDays] = useState(user.ghost_after_days)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const zones = useMemo(() => allTimezones(user.timezone), [user.timezone])
  const detected = browserTimezone()

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const updated = await api<User>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          display_name: name || null,
          timezone,
          weekly_goal: goal,
          ghost_after_days: ghostDays,
        }),
      })
      queryClient.setQueryData(['me'], updated)
      refreshPipelineData(queryClient)
      setMessage('Saved.')
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="font-serif text-4xl">Settings</h1>
      {user.is_demo && (
        <p className="mt-3 rounded-xl border border-gold/40 bg-gold/10 p-3 text-sm text-gold">
          This is the shared demo account, so these are locked.
        </p>
      )}
      <form onSubmit={onSubmit} className="mt-6 grid gap-4">
        <Field label="Name">
          <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} />
        </Field>
        <Field label="Timezone (weeks start Monday here)">
          <Select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {zones.map((zone) => (
              <option key={zone}>{zone}</option>
            ))}
          </Select>
        </Field>
        {detected !== timezone && (
          <button
            type="button"
            className="-mt-2 justify-self-start text-xs text-ember-2 underline"
            onClick={() => setTimezone(detected)}
          >
            Use this browser's timezone ({detected})
          </button>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Weekly goal">
            <Input
              type="number"
              min={1}
              max={100}
              value={goal}
              onChange={(e) => setGoal(Number(e.target.value))}
            />
          </Field>
          <Field label="Ghost after (days)">
            <Input
              type="number"
              min={1}
              max={120}
              value={ghostDays}
              onChange={(e) => setGhostDays(Number(e.target.value))}
            />
          </Field>
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy || user.is_demo}>
            {busy ? 'Saving…' : 'Save'}
          </Button>
          {message && <span className="text-sm text-tan">{message}</span>}
        </div>
      </form>
    </div>
  )
}
