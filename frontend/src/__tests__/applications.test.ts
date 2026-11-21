import { describe, expect, it } from 'vitest'

import { listQueryString } from '@/lib/applications'

describe('listQueryString', () => {
  it('drops empty filters so the api gets clean params', () => {
    const query = new URLSearchParams(
      listQueryString({ q: '', status: '', source: 'Referral', sort: 'company' }, 2, 250),
    )
    expect(Object.fromEntries(query)).toEqual({
      page: '2',
      page_size: '250',
      source: 'Referral',
      sort: 'company',
    })
  })

  it('encodes search text', () => {
    expect(listQueryString({ q: 'a&b c' }, 1, 50)).toContain('q=a%26b+c')
  })
})
