import { useInfiniteQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useEffect, useRef, useState } from 'react'

import { StatusPill } from '@/components/StatusPill'
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

const PAGE_SIZE = 250
const ROW_HEIGHT = 44

// One grid for header + rows so columns line up without a real <table>.
const GRID =
  'grid grid-cols-[1.2fr_1.2fr_96px_72px] sm:grid-cols-[1.2fr_1.2fr_96px_72px_72px] md:grid-cols-[1.2fr_1.4fr_96px_1fr_80px_80px]'

type SortKey = NonNullable<ListParams['sort']>

const columns: { key: SortKey | null; label: string; className?: string }[] = [
  { key: 'company', label: 'Company' },
  { key: 'role', label: 'Role' },
  { key: 'status', label: 'Status' },
  { key: null, label: 'Source', className: 'hidden md:block' },
  { key: 'applied_at', label: 'Applied' },
  { key: 'updated_at', label: 'Updated', className: 'hidden sm:block' },
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

  // Only the rows on screen exist in the DOM. 10k rows scroll like 30.
  const scrollRef = useRef<HTMLDivElement>(null)
  // no React Compiler here, so this warning doesn't apply
  // oxlint-disable-next-line react/incompatible-library
  const virtualizer = useVirtualizer({
    count: query.hasNextPage ? rows.length + 1 : rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  })
  const items = virtualizer.getVirtualItems()
  const lastIndex = items.length ? items[items.length - 1].index : -1

  // Pull the next page once the "loading…" row scrolls into view.
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = query
  useEffect(() => {
    if (lastIndex >= rows.length - 1 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [lastIndex, rows.length, hasNextPage, isFetchingNextPage, fetchNextPage])

  // New filter = start back at the top.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 })
  }, [q, status, source, sort, direction])

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

      <div
        className="overflow-hidden rounded-2xl border border-line bg-raised/70"
        role="table"
      >
        <div
          role="row"
          className={cn(
            GRID,
            'border-b border-line font-mono text-[11px] tracking-wide text-tan uppercase',
          )}
        >
          {columns.map((column) => (
            <div
              key={column.label}
              role="columnheader"
              className={cn('px-3 py-2.5 font-normal', column.className)}
            >
              {column.key ? (
                <button
                  type="button"
                  onClick={() => toggleSort(column.key!)}
                  className="inline-flex items-center gap-1 uppercase hover:text-cream"
                >
                  {column.label}
                  {sort === column.key &&
                    (direction === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                </button>
              ) : (
                column.label
              )}
            </div>
          ))}
        </div>
        <div ref={scrollRef} className="h-[65vh] overflow-y-auto" role="rowgroup">
          <div className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((item) => {
              const row = rows[item.index]
              return (
                <div
                  key={row?.id ?? item.key}
                  className="absolute top-0 left-0 w-full"
                  style={{ height: item.size, transform: `translateY(${item.start}px)` }}
                >
                  {row ? (
                    <Row row={row} onOpen={onOpen} />
                  ) : (
                    <div className="px-3 py-2.5 font-mono text-xs text-tan">loading…</div>
                  )}
                </div>
              )
            })}
          </div>
          {!query.isLoading && rows.length === 0 && (
            <p className="px-4 py-10 text-center text-tan">Nothing matches that.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ row, onOpen }: { row: Application; onOpen: (row: Application) => void }) {
  return (
    <div
      role="row"
      tabIndex={0}
      onClick={() => onOpen(row)}
      onKeyDown={(event) => event.key === 'Enter' && onOpen(row)}
      className={cn(
        GRID,
        'h-full cursor-pointer items-center border-b border-line/50 text-sm hover:bg-raised-2/70 focus-visible:bg-raised-2/70 focus-visible:outline-none',
      )}
    >
      <div role="cell" className="truncate px-3 font-medium">
        {row.company}
      </div>
      <div role="cell" className="truncate px-3 text-tan">
        {row.role}
      </div>
      <div role="cell" className="px-3">
        <StatusPill status={row.status} />
      </div>
      <div role="cell" className="hidden truncate px-3 text-tan md:block">
        {row.source ?? '—'}
      </div>
      <div role="cell" className="px-3 font-mono text-xs text-tan">
        {formatDay(row.applied_at)}
      </div>
      <div role="cell" className="hidden px-3 font-mono text-xs text-tan sm:block">
        {new Date(row.updated_at).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
        })}
      </div>
    </div>
  )
}
