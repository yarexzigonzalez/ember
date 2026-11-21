import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Upload } from 'lucide-react'
import { useState, type ChangeEvent } from 'react'

import { Button } from '@/components/ui/button'
import { TextArea } from '@/components/ui/input'
import { ApiError, api } from '@/lib/api'
import { refreshPipelineData } from '@/lib/applications'

type ImportResult = {
  added: number
  skipped: number
  errors: { row: number; message: string }[]
}

const MAX_BYTES = 2 * 1024 * 1024
const SAMPLE = `company,role,link,date
Stripe,Backend Intern,https://stripe.com/jobs/1,2026-10-01
Notion,New Grad SWE,,2026-10-03`

export function Import() {
  const queryClient = useQueryClient()
  const [text, setText] = useState('')
  const [fileError, setFileError] = useState<string | null>(null)

  const run = useMutation({
    mutationFn: () =>
      api<ImportResult>('/import', { method: 'POST', body: JSON.stringify({ csv: text }) }),
    onSuccess: () => refreshPipelineData(queryClient),
  })

  async function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    setFileError(null)
    if (!file) return
    if (file.size > MAX_BYTES) {
      setFileError('That file is over 2 MB.')
      return
    }
    setText(await file.text())
  }

  return (
    <div className="grid max-w-3xl gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-4xl">Import</h1>
          <p className="mt-1 text-sm text-tan">
            CSV with <code className="font-mono text-cream">company, role, link, date</code>
            . Headers can be any case, extra columns get ignored, date is YYYY-MM-DD. Up to
            5,000 rows.
          </p>
        </div>
        <Button asChild variant="quiet">
          <a href="/api/export.csv" download>
            <Download size={14} /> Export CSV
          </a>
        </Button>
      </div>

      <TextArea
        className="min-h-64 font-mono text-xs"
        placeholder={SAMPLE}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="flex flex-wrap items-center gap-3">
        <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-full border border-line bg-raised px-4 text-sm hover:border-tan/40">
          <Upload size={14} /> Pick a file
          <input
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            onChange={pickFile}
          />
        </label>
        <Button onClick={() => run.mutate()} disabled={!text.trim() || run.isPending}>
          {run.isPending ? 'Importing…' : 'Import'}
        </Button>
        {fileError && <span className="text-sm text-rose">{fileError}</span>}
      </div>

      {run.error && (
        <p className="text-sm text-rose">
          {run.error instanceof ApiError ? run.error.message : 'Import failed'}
        </p>
      )}

      {run.data && (
        <section className="rounded-2xl border border-line bg-raised/70 p-4">
          <p className="font-serif text-xl">
            Added {run.data.added}, skipped {run.data.skipped} already on the board
            {run.data.errors.length > 0 && `, ${run.data.errors.length} had problems`}.
          </p>
          {run.data.errors.length > 0 && (
            <ul className="mt-3 grid max-h-64 gap-1 overflow-y-auto font-mono text-xs text-tan">
              {run.data.errors.map((error) => (
                <li key={error.row}>
                  row {error.row}: <span className="text-rose">{error.message}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
