import { useInfiniteQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useState } from 'react'

import { StatusPill } from '@/components/StatusPill'
import { Button } from '@/components/ui/button'
import { Input, Select } from '@/components/ui/input'
import { api } from '@/lib/api'
import { listQueryString, type ListParams } from '@/lib/applications'
import { formatDay } from '@/lib/dates'
import {
  SOURCES,
  STATUSES,
  type Application,
  type ApplicationList,
  type Status,
} from '@/lib/types'
import { cn } from '@/lib/utils'

const PAGE_SIZE = 100

type SortKey = NonNullable<ListParams['sort']>

const columns: { key: SortKey | null; label: string; className?: string }[] = [
  { key: 'company', label: 'Company' },
  { key: 'role', label: 'Role' },
  { key: 'status', label: 'Status' },
  { key: null, label: 'Source', className: 'hidden md:table-cell' },
  { key: 'applied_at', label: 'Applied' },
  { key: 'updated_at', label: 'Updated', className: 'hidden sm:table-cell' },
]

export function Table({ onOpen }: { onOpen: (row: Application) => void }) {
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<Status | ''>('')
  const [source, setSource] = useState('')
  const [sort, setSort] = useState<SortKey>('updated_at')
  const [direction, setDirection] = useState<'asc' | 'desc'>('desc')

  // Don't hit the API on every keystroke.
  useEffect(() => {
    const id = setTimeout(() => setQ(search.trim()), 250)
    return () => clearTimeout(id)
  }, [search])

  const params: ListParams = { q, status, source, sort, direction }
  const query = useInfiniteQuery({
    queryKey: ['applications', 'table', params],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api<ApplicationList>(
        `/applications?${listQueryString(params, pageParam, PAGE_SIZE)}`,
      ),
    getNextPageParam: (last) =>
      last.page * last.page_size < last.total ? last.page + 1 : undefined,
  })

  const rows = query.data?.pages.flatMap((page) => page.items) ?? []
  const total = query.data?.pages[0]?.total ?? 0

  function toggleSort(key: SortKey) {
    if (key === sort) {
      setDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
    } else {
      setSort(key)
      setDirection(key === 'updated_at' || key === 'applied_at' ? 'desc' : 'asc')
    }
  }

  return (
    <div className="grid gap-3">
      <div className="grid gap-2 sm:grid-cols-[1fr_160px_160px]">
        <Input
          placeholder="Search company, role, location"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <Select
          value={status}
          onChange={(event) => setStatus(event.target.value as Status | '')}
        >
          <option value="">Any status</option>
          {STATUSES.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="">Any source</option>
          {SOURCES.map((item) => (
            <option key={item}>{item}</option>
          ))}
        </Select>
      </div>

      <p className="font-mono text-xs text-tan">
        {query.isLoading
          ? 'loading…'
          : `${total.toLocaleString()} ${total === 1 ? 'row' : 'rows'}`}
      </p>

      <div className="overflow-hidden rounded-2xl border border-line bg-raised/70">
        <table className="w-full table-fixed text-left text-sm">
          <thead className="border-b border-line font-mono text-[11px] tracking-wide text-tan uppercase">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.label}
                  className={cn('px-3 py-2.5 font-normal', column.className)}
                >
                  {column.key ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key!)}
                      className="inline-flex items-center gap-1 hover:text-cream"
                    >
                      {column.label}
                      {sort === column.key &&
                        (direction === 'asc' ? (
                          <ArrowUp size={12} />
                        ) : (
                          <ArrowDown size={12} />
                        ))}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Row key={row.id} row={row} onOpen={onOpen} />
            ))}
          </tbody>
        </table>
        {!query.isLoading && rows.length === 0 && (
          <p className="px-4 py-10 text-center text-tan">Nothing matches that.</p>
        )}
      </div>

      {query.hasNextPage && (
        <Button
          variant="quiet"
          className="justify-self-center"
          onClick={() => query.fetchNextPage()}
          disabled={query.isFetchingNextPage}
        >
          {query.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </Button>
      )}
    </div>
  )
}

function Row({ row, onOpen }: { row: Application; onOpen: (row: Application) => void }) {
  return (
    <tr
      onClick={() => onOpen(row)}
      className="cursor-pointer border-b border-line/50 last:border-0 hover:bg-raised-2/70"
    >
      <td className="truncate px-3 py-2.5 font-medium">{row.company}</td>
      <td className="truncate px-3 py-2.5 text-tan">{row.role}</td>
      <td className="px-3 py-2.5">
        <StatusPill status={row.status} />
      </td>
      <td className="hidden truncate px-3 py-2.5 text-tan md:table-cell">
        {row.source ?? '—'}
      </td>
      <td className="px-3 py-2.5 font-mono text-xs text-tan">
        {formatDay(row.applied_at)}
      </td>
      <td className="hidden px-3 py-2.5 font-mono text-xs text-tan sm:table-cell">
        {new Date(row.updated_at).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
        })}
      </td>
    </tr>
  )
}
