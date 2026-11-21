import { useMutation } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'

import { ApplicationForm } from '@/components/pipeline/ApplicationForm'
import { Button } from '@/components/ui/button'
import { TextArea } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import type { ApplicationInput } from '@/lib/types'

type Extracted = {
  job: {
    company: string | null
    role: string | null
    location: string | null
    posting_url: string | null
    seniority: string
    role_type: string
    requirements: string[]
  }
  via: 'cache' | 'llm' | 'heuristic'
}

const viaLabel = {
  llm: 'read by the model',
  cache: 'seen this one before, pulled from cache',
  heuristic: 'quick regex pass, double-check it',
}

const MAX = 20_000

// Step 1: paste. Step 2: the normal form, pre-filled, so nothing saves without a look.
export function QuickAdd({
  onSaved,
  onCancel,
}: {
  onSaved: () => void
  onCancel: () => void
}) {
  const [text, setText] = useState('')
  const extract = useMutation({
    mutationFn: () =>
      api<Extracted>('/extract', { method: 'POST', body: JSON.stringify({ text }) }),
  })

  if (extract.data) {
    const { job, via } = extract.data
    const prefill: Partial<ApplicationInput> = {
      company: job.company ?? '',
      role: job.role ?? '',
      location: job.location ?? '',
      posting_url: job.posting_url ?? '',
      seniority: job.seniority,
      role_type: job.role_type,
      requirements: job.requirements,
    }
    return (
      <div className="grid gap-4">
        <p className="flex items-center gap-2 font-mono text-[11px] text-tan">
          <Sparkles size={12} className="text-ember-2" /> {viaLabel[via]}
        </p>
        {job.requirements.length > 0 && (
          <ul className="grid gap-1 rounded-xl border border-line bg-ink/60 p-3 text-xs text-tan">
            {job.requirements.map((item) => (
              <li key={item}>· {item}</li>
            ))}
          </ul>
        )}
        <ApplicationForm prefill={prefill} onSaved={onSaved} onCancel={onCancel} />
      </div>
    )
  }

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        extract.mutate()
      }}
    >
      <TextArea
        autoFocus
        className="min-h-64 font-mono text-xs"
        placeholder="Paste the whole job post. Title, company, the requirements list, all of it."
        value={text}
        maxLength={MAX}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] text-tan/70">
          {text.length.toLocaleString()} / {MAX.toLocaleString()}
        </span>
        <div className="flex gap-2">
          <Button variant="quiet" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={text.trim().length < 20 || extract.isPending}>
            {extract.isPending ? 'Reading…' : 'Pull out the fields'}
          </Button>
        </div>
      </div>
      {extract.error && (
        <p className="text-sm text-rose">
          {extract.error instanceof ApiError
            ? extract.error.message
            : 'Could not read that'}
        </p>
      )}
    </form>
  )
}
