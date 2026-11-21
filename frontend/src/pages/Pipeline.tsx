import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Columns3, Plus, Rows3 } from 'lucide-react'
import { useState } from 'react'

import { ApplicationForm } from '@/components/pipeline/ApplicationForm'
import { Board } from '@/components/pipeline/Board'
import { Table } from '@/components/pipeline/Table'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { refreshPipelineData, useAllApplications } from '@/lib/applications'
import type { Application } from '@/lib/types'
import { cn } from '@/lib/utils'

type View = 'board' | 'table'

export function Pipeline() {
  const queryClient = useQueryClient()
  const all = useAllApplications()
  const [view, setView] = useState<View>(() =>
    localStorageGet('ember:view') === 'table' ? 'table' : 'board',
  )
  const [editing, setEditing] = useState<Application | null>(null)
  const [adding, setAdding] = useState(false)

  function pickView(next: View) {
    setView(next)
    localStorageSet('ember:view', next)
  }

  function closeForm() {
    setEditing(null)
    setAdding(false)
  }

  function saved() {
    closeForm()
    refreshPipelineData(queryClient)
  }

  const count = all.data?.length ?? 0

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-4xl">Pipeline</h1>
          <p className="mt-1 text-sm text-tan">
            {all.isLoading
              ? 'Loading…'
              : `${count} ${count === 1 ? 'job' : 'jobs'} in play`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-full border border-line bg-raised p-0.5">
            <ViewButton active={view === 'board'} onClick={() => pickView('board')}>
              <Columns3 size={14} /> Board
            </ViewButton>
            <ViewButton active={view === 'table'} onClick={() => pickView('table')}>
              <Rows3 size={14} /> Table
            </ViewButton>
          </div>
          <Button onClick={() => setAdding(true)}>
            <Plus size={16} /> Add job
          </Button>
        </div>
      </div>

      <motion.div
        key={view}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
      >
        {view === 'board' ? (
          all.isError ? (
            <p className="text-rose">Couldn't load your pipeline.</p>
          ) : (
            <Board rows={all.data ?? []} onOpen={setEditing} />
          )
        ) : (
          <Table onOpen={setEditing} />
        )}
      </motion.div>

      {!all.isLoading && count === 0 && view === 'board' && (
        <p className="text-center text-sm text-tan">
          Empty board. Hit <span className="text-cream">Add job</span> and drop your first
          one in.
        </p>
      )}

      <Dialog
        open={adding || editing !== null}
        onOpenChange={(open) => !open && closeForm()}
        title={editing ? 'Edit job' : 'Add a job'}
      >
        <ApplicationForm
          key={editing?.id ?? 'new'}
          initial={editing}
          onSaved={saved}
          onCancel={closeForm}
        />
      </Dialog>
    </div>
  )
}

function ViewButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs transition-colors',
        active ? 'bg-raised-2 text-cream' : 'text-tan hover:text-cream',
      )}
    >
      {children}
    </button>
  )
}

function localStorageGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function localStorageSet(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // private mode or blocked storage, whatever, it's just a preference
  }
}
