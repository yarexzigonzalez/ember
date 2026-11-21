import { cn } from '@/lib/utils'
import type { Status } from '@/lib/types'

const tones: Record<Status, string> = {
  saved: 'bg-tan/15 text-tan',
  applied: 'bg-ember/20 text-ember-2',
  oa: 'bg-gold/20 text-gold',
  interview: 'bg-rose/20 text-rose',
  offer: 'bg-moss/25 text-moss',
  rejected: 'bg-oxblood/40 text-rose',
  ghosted: 'bg-line text-tan',
}

export function StatusPill({ status }: { status: Status }) {
  const label = status === 'oa' ? 'OA' : status[0].toUpperCase() + status.slice(1)
  return (
    <span
      className={cn(
        'rounded-full px-2 py-0.5 font-mono text-[11px] tracking-wide',
        tones[status],
      )}
    >
      {label}
    </span>
  )
}
