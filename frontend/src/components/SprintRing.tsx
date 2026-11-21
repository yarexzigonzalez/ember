import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Flame } from 'lucide-react'

import { api } from '@/lib/api'
import { parseDay } from '@/lib/dates'

type Sprint = {
  goal: number
  week_start: string
  week_end: string
  count: number
  streak: number
  history: { week_start: string; count: number }[]
}

const R = 34
const CIRC = 2 * Math.PI * R

export function SprintRing() {
  const sprint = useQuery({ queryKey: ['sprint'], queryFn: () => api<Sprint>('/sprint') })
  if (!sprint.data)
    return <div className="h-[104px] rounded-2xl border border-line bg-raised/70" />
  const { goal, count, streak, history, week_start, week_end } = sprint.data
  const progress = Math.min(1, count / goal)
  const best = Math.max(goal, ...history.map((week) => week.count))
  const range = `${parseDay(week_start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${parseDay(week_end).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`

  return (
    <section className="flex flex-wrap items-center gap-5 rounded-2xl border border-line bg-raised/70 p-4">
      <div className="relative size-20 shrink-0">
        <svg viewBox="0 0 80 80" className="size-20 -rotate-90">
          <circle cx="40" cy="40" r={R} className="fill-none stroke-line" strokeWidth="7" />
          <motion.circle
            cx="40"
            cy="40"
            r={R}
            className="fill-none stroke-ember"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            initial={{ strokeDashoffset: CIRC }}
            animate={{ strokeDashoffset: CIRC * (1 - progress) }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center font-mono text-sm">
          {count}/{goal}
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-serif text-xl">
          {count >= goal ? 'Goal hit this week.' : `${goal - count} more to hit the week.`}
        </p>
        <p className="mt-1 font-mono text-xs text-tan">{range}</p>
        <p className="mt-2 flex items-center gap-1.5 text-sm text-tan">
          <Flame size={14} className={streak > 0 ? 'text-ember-2' : ''} />
          {streak === 0 ? 'No streak yet' : `${streak}-week streak`}
        </p>
      </div>
      <div className="flex h-14 items-end gap-1" aria-label="Last 8 weeks">
        {history.map((week) => (
          <div
            key={week.week_start}
            title={`${week.week_start}: ${week.count}`}
            className={
              week.count >= goal ? 'w-2.5 rounded-sm bg-ember' : 'w-2.5 rounded-sm bg-line'
            }
            style={{ height: `${Math.max(6, (week.count / best) * 100)}%` }}
          />
        ))}
      </div>
    </section>
  )
}
