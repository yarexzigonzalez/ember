import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export type Bucket = {
  key: string
  applied: number
  responded: number
  rate: number | null
}

const pct = (value: number | null) => (value === null ? '—' : `${Math.round(value * 100)}%`)

// One series (response rate), one hue. Bars end-rounded, grid kept quiet.
export function RateChart({
  title,
  buckets,
  layout = 'horizontal',
  label = (key: string) => key,
}: {
  title: string
  buckets: Bucket[]
  layout?: 'horizontal' | 'vertical'
  label?: (key: string) => string
}) {
  const [asTable, setAsTable] = useState(false)
  const data = buckets.map((b) => ({ ...b, name: label(b.key), pct: (b.rate ?? 0) * 100 }))
  const sideways = layout === 'vertical'
  const height = sideways ? Math.max(140, data.length * 34 + 30) : 220

  return (
    <section className="rounded-2xl border border-line bg-raised/70 p-4">
      <header className="mb-3 flex items-center justify-between">
        <h2 className="font-serif text-xl">{title}</h2>
        <button
          type="button"
          onClick={() => setAsTable((v) => !v)}
          className="font-mono text-[11px] text-tan underline-offset-2 hover:text-cream hover:underline"
        >
          {asTable ? 'chart' : 'table'}
        </button>
      </header>
      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-tan">No applied jobs yet.</p>
      ) : asTable ? (
        <table className="w-full text-sm">
          <thead className="font-mono text-[11px] text-tan uppercase">
            <tr>
              <th className="py-1 text-left font-normal">Bucket</th>
              <th className="py-1 text-right font-normal">Applied</th>
              <th className="py-1 text-right font-normal">Heard back</th>
              <th className="py-1 text-right font-normal">Rate</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs">
            {data.map((row) => (
              <tr key={row.key} className="border-t border-line/50">
                <td className="py-1.5 font-sans text-sm">{row.name}</td>
                <td className="py-1.5 text-right">{row.applied}</td>
                <td className="py-1.5 text-right">{row.responded}</td>
                <td className="py-1.5 text-right">{pct(row.rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout={sideways ? 'vertical' : 'horizontal'}
              margin={{ top: 4, right: 12, bottom: 0, left: 0 }}
              barCategoryGap={sideways ? 8 : '22%'}
            >
              <CartesianGrid
                stroke="var(--color-line)"
                strokeOpacity={0.5}
                vertical={sideways}
                horizontal={!sideways}
              />
              {sideways ? (
                <>
                  <XAxis type="number" domain={[0, 100]} unit="%" {...axis} />
                  <YAxis type="category" dataKey="name" width={96} {...axis} />
                </>
              ) : (
                <>
                  <XAxis dataKey="name" {...axis} />
                  <YAxis domain={[0, 100]} unit="%" width={40} {...axis} />
                </>
              )}
              <Tooltip
                cursor={{ fill: 'var(--color-raised-2)', opacity: 0.6 }}
                content={<RateTooltip />}
              />
              <Bar
                dataKey="pct"
                fill="var(--color-ember)"
                radius={sideways ? [0, 4, 4, 0] : [4, 4, 0, 0]}
                maxBarSize={28}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}

const axis = {
  tick: { fill: 'var(--color-tan)', fontSize: 11 },
  axisLine: false,
  tickLine: false,
} as const

function RateTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: Bucket & { name: string } }[]
}) {
  const row = payload?.[0]?.payload
  if (!active || !row) return null
  return (
    <div className="rounded-lg border border-line bg-ink px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-cream">{row.name}</p>
      <p className="mt-1 font-mono text-tan">
        {pct(row.rate)} · {row.responded} of {row.applied} heard back
      </p>
    </div>
  )
}
