import { useQuery } from '@tanstack/react-query'

import { RateChart, type Bucket } from '@/components/analytics/RateChart'
import { api } from '@/lib/api'
import { ROLE_TYPES } from '@/lib/types'

type Pulse = {
  applied: number
  responded: number
  response_rate: number | null
  median_days_to_response: number | null
  by_source: Bucket[]
  by_role_type: Bucket[]
  by_weekday: Bucket[]
}

const roleLabel = (key: string) => ROLE_TYPES.find((r) => r.id === key)?.label ?? key

export function Pulse() {
  const pulse = useQuery({
    queryKey: ['pulse'],
    queryFn: () => api<Pulse>('/analytics/pulse'),
  })
  const data = pulse.data

  return (
    <div className="grid gap-5">
      <div>
        <h1 className="font-serif text-4xl">Market Pulse</h1>
        <p className="mt-1 max-w-xl text-sm text-tan">
          What actually gets a reply. A response is the first OA, interview, offer, or
          rejection. Saved jobs you never sent don't count.
        </p>
      </div>

      {pulse.isLoading && <p className="text-tan">Crunching…</p>}
      {pulse.isError && <p className="text-rose">Couldn't load the numbers.</p>}

      {data && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Applied" value={data.applied.toLocaleString()} />
            <Stat
              label="Response rate"
              value={
                data.response_rate === null
                  ? '—'
                  : `${Math.round(data.response_rate * 100)}%`
              }
              hint={`${data.responded} heard back`}
            />
            <Stat
              label="Median wait for a reply"
              value={
                data.median_days_to_response === null
                  ? '—'
                  : `${data.median_days_to_response.toFixed(data.median_days_to_response % 1 ? 1 : 0)}d`
              }
            />
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <RateChart title="By source" buckets={data.by_source} layout="vertical" />
            <RateChart
              title="By role type"
              buckets={data.by_role_type}
              layout="vertical"
              label={roleLabel}
            />
          </div>
          <RateChart
            title="By day you applied"
            buckets={data.applied ? data.by_weekday : []}
          />
        </>
      )}
    </div>
  )
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-raised/70 p-4">
      <p className="font-mono text-[11px] tracking-wide text-tan uppercase">{label}</p>
      <p className="mt-2 font-serif text-4xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-tan">{hint}</p>}
    </div>
  )
}
