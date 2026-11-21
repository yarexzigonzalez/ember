import { describe, expect, it } from 'vitest'

import { daysSince, formatDay, parseDay } from '@/lib/dates'

describe('parseDay', () => {
  it('keeps the calendar date instead of shifting it through UTC', () => {
    // new Date('2026-11-16') would be UTC midnight, which is the 15th in LA
    const day = parseDay('2026-11-16')
    expect([day.getFullYear(), day.getMonth(), day.getDate()]).toEqual([2026, 10, 16])
  })
})

describe('formatDay', () => {
  it('shows a dash for missing dates', () => {
    expect(formatDay(null)).toBe('—')
  })
  it('formats real ones with the day intact', () => {
    expect(formatDay('2026-01-05')).toMatch(/5/)
  })
})

describe('daysSince', () => {
  const now = new Date('2026-11-20T12:00:00Z')
  it('counts whole days', () => {
    expect(daysSince('2026-11-10T12:00:00Z', now)).toBe(10)
    expect(daysSince('2026-11-20T01:00:00Z', now)).toBe(0)
  })
  it('never goes negative for future timestamps', () => {
    expect(daysSince('2026-12-01T00:00:00Z', now)).toBe(0)
  })
})
