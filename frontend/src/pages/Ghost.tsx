import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Check, Copy, Ghost as GhostIcon, Mail } from 'lucide-react'
import { useState } from 'react'

import { StatusPill } from '@/components/StatusPill'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { TextArea } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import { refreshPipelineData } from '@/lib/applications'
import { formatDay } from '@/lib/dates'
import type { Application } from '@/lib/types'

type GhostList = {
  after_days: number
  items: { application: Application; days_quiet: number }[]
}
type Draft = { text: string; via: 'llm' | 'template' }

export function Ghost() {
  const queryClient = useQueryClient()
  const ghosts = useQuery({ queryKey: ['ghost'], queryFn: () => api<GhostList>('/ghost') })
  const [drafting, setDrafting] = useState<Application | null>(null)

  const markGhosted = useMutation({
    mutationFn: (id: string) =>
      api(`/applications/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'ghosted' }),
      }),
    onSettled: () => refreshPipelineData(queryClient),
  })

  const items = ghosts.data?.items ?? []

  return (
    <div className="grid gap-5">
      <div>
        <h1 className="font-serif text-4xl">Ghost Radar</h1>
        <p className="mt-1 max-w-xl text-sm text-tan">
          Open applications with no movement in {ghosts.data?.after_days ?? '…'}+ days.
          Nudge them or call it. Nothing gets moved to Ghosted unless you say so.
        </p>
      </div>

      {ghosts.isLoading && <p className="text-tan">Scanning…</p>}
      {!ghosts.isLoading && items.length === 0 && (
        <div className="rounded-2xl border border-line bg-raised/70 p-10 text-center">
          <GhostIcon className="mx-auto text-tan" />
          <p className="mt-3 text-tan">Nothing's gone cold. Nice.</p>
        </div>
      )}

      <div className="grid gap-2">
        {items.map(({ application, days_quiet }, index) => (
          <motion.div
            key={application.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, delay: Math.min(index, 8) * 0.03 }}
            className="flex flex-wrap items-center gap-3 rounded-2xl border border-line bg-raised/70 p-4"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{application.company}</p>
              <p className="truncate text-sm text-tan">{application.role}</p>
            </div>
            <StatusPill status={application.status} />
            <div className="w-28 text-right font-mono text-xs text-tan">
              <span className="text-lg text-ember-2">{days_quiet}</span>d quiet
              <br />
              applied {formatDay(application.applied_at)}
            </div>
            <div className="flex w-full gap-2 sm:w-auto">
              <Button size="sm" variant="quiet" onClick={() => setDrafting(application)}>
                <Mail size={14} /> Draft follow-up
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => markGhosted.mutate(application.id)}
                disabled={markGhosted.isPending}
              >
                Mark ghosted
              </Button>
            </div>
          </motion.div>
        ))}
      </div>

      <Dialog
        open={drafting !== null}
        onOpenChange={(open) => !open && setDrafting(null)}
        title="Follow-up draft"
      >
        {drafting && <DraftBox application={drafting} />}
      </Dialog>
    </div>
  )
}

function DraftBox({ application }: { application: Application }) {
  const [copied, setCopied] = useState(false)
  const draft = useQuery({
    queryKey: ['draft', application.id],
    queryFn: () => api<Draft>(`/ghost/${application.id}/draft`, { method: 'POST' }),
    staleTime: Infinity,
    retry: false,
  })
  const [text, setText] = useState<string | null>(null)
  const value = text ?? draft.data?.text ?? ''

  async function copy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard blocked; the text is right there to select by hand
    }
  }

  if (draft.isLoading) return <p className="text-tan">Writing something not cringe…</p>
  if (draft.error) {
    return (
      <p className="text-rose">
        {draft.error instanceof ApiError ? draft.error.message : 'Could not draft that'}
      </p>
    )
  }
  return (
    <div className="grid gap-3">
      <p className="font-mono text-[11px] text-tan">
        {draft.data?.via === 'llm' ? 'written by the model' : 'template, tweak it'}
      </p>
      <TextArea
        className="min-h-56"
        value={value}
        onChange={(e) => setText(e.target.value)}
      />
      <Button onClick={copy} className="justify-self-end">
        {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? 'Copied' : 'Copy'}
      </Button>
    </div>
  )
}
