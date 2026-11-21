import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Field, Input, Select, TextArea } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import {
  ROLE_TYPES,
  SENIORITY,
  SOURCES,
  STATUSES,
  type Application,
  type ApplicationInput,
  type Status,
} from '@/lib/types'

const empty: ApplicationInput = {
  company: '',
  role: '',
  location: '',
  source: 'LinkedIn',
  posting_url: '',
  status: 'saved',
  seniority: 'intern',
  role_type: 'intern',
  notes: '',
}

export function ApplicationForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: Application | null
  onSaved: () => void
  onCancel: () => void
}) {
  const [form, setForm] = useState<ApplicationInput>(
    initial
      ? {
          company: initial.company,
          role: initial.role,
          location: initial.location ?? '',
          source: initial.source ?? '',
          posting_url: initial.posting_url ?? '',
          status: initial.status,
          seniority: initial.seniority ?? '',
          role_type: initial.role_type ?? '',
          notes: initial.notes ?? '',
          applied_at: initial.applied_at,
        }
      : empty,
  )
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function set<K extends keyof ApplicationInput>(key: K, value: ApplicationInput[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const payload = {
      ...form,
      location: form.location || null,
      source: form.source || null,
      posting_url: form.posting_url || null,
      seniority: form.seniority || null,
      role_type: form.role_type || null,
      notes: form.notes || null,
      // blank means "let the server stamp it when it hits Applied"
      applied_at: form.applied_at || null,
    }
    try {
      if (initial) {
        await api(`/applications/${initial.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      } else {
        await api('/applications', { method: 'POST', body: JSON.stringify(payload) })
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  async function onDelete() {
    if (!initial) return
    setBusy(true)
    try {
      await api(`/applications/${initial.id}`, { method: 'DELETE' })
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete')
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Company">
          <Input
            required
            value={form.company}
            onChange={(e) => set('company', e.target.value)}
          />
        </Field>
        <Field label="Role">
          <Input required value={form.role} onChange={(e) => set('role', e.target.value)} />
        </Field>
        <Field label="Location">
          <Input
            value={form.location ?? ''}
            onChange={(e) => set('location', e.target.value)}
          />
        </Field>
        <Field label="Link">
          <Input
            value={form.posting_url ?? ''}
            onChange={(e) => set('posting_url', e.target.value)}
          />
        </Field>
        <Field label="Source">
          <Select value={form.source ?? ''} onChange={(e) => set('source', e.target.value)}>
            <option value="">—</option>
            {SOURCES.map((source) => (
              <option key={source}>{source}</option>
            ))}
          </Select>
        </Field>
        <Field label="Status">
          <Select
            value={form.status}
            onChange={(e) => set('status', e.target.value as Status)}
          >
            {STATUSES.map((status) => (
              <option key={status.id} value={status.id}>
                {status.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Seniority">
          <Select
            value={form.seniority ?? ''}
            onChange={(e) => set('seniority', e.target.value)}
          >
            <option value="">—</option>
            {SENIORITY.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Applied on">
          <Input
            type="date"
            value={form.applied_at ?? ''}
            onChange={(e) => set('applied_at', e.target.value)}
          />
        </Field>
        <Field label="Role type">
          <Select
            value={form.role_type ?? ''}
            onChange={(e) => set('role_type', e.target.value)}
          >
            <option value="">—</option>
            {ROLE_TYPES.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <Field label="Notes">
        <TextArea value={form.notes ?? ''} onChange={(e) => set('notes', e.target.value)} />
      </Field>
      {error && <p className="text-sm text-rose">{error}</p>}
      <div className="flex items-center justify-between gap-3">
        {initial ? (
          <Button variant="danger" size="sm" onClick={onDelete} disabled={busy}>
            Delete
          </Button>
        ) : (
          <span />
        )}
        <div className="flex gap-2">
          <Button variant="quiet" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>
    </form>
  )
}
