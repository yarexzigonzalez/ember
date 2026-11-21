// applied_at comes over as a plain YYYY-MM-DD. Don't feed it to new Date()
// directly or the browser treats it as UTC midnight and shifts it a day.
export function parseDay(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatDay(value: string | null): string {
  if (!value) return '—'
  return parseDay(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function daysSince(iso: string, now = new Date()): number {
  const ms = now.getTime() - new Date(iso).getTime()
  return Math.max(0, Math.floor(ms / 86_400_000))
}

export function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}
