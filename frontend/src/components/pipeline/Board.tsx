import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'

import { useMoveApplication } from '@/lib/applications'
import { daysSince } from '@/lib/dates'
import { STATUSES, type Application, type Status } from '@/lib/types'
import { cn } from '@/lib/utils'

// Board isn't virtualized, so cap what each column renders. Table handles the long tail.
const PER_COLUMN = 60

const accents: Record<Status, string> = {
  saved: 'bg-tan',
  applied: 'bg-ember',
  oa: 'bg-gold',
  interview: 'bg-rose',
  offer: 'bg-moss',
  rejected: 'bg-oxblood',
  ghosted: 'bg-line',
}

export function Board({
  rows,
  onOpen,
  readOnly = false,
}: {
  rows: Application[]
  onOpen: (row: Application) => void
  readOnly?: boolean
}) {
  const move = useMoveApplication()
  const sensors = useSensors(
    // A little drag distance so a plain click still opens the card.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor),
  )

  function onDragEnd(event: DragEndEvent) {
    const target = event.over?.id as Status | undefined
    const row = rows.find((item) => item.id === event.active.id)
    if (!target || !row || row.status === target) return
    move.mutate({ id: row.id, status: target })
  }

  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <div className="-mx-4 overflow-x-auto px-4 pb-4 md:mx-0 md:px-0">
        <div className="grid min-w-[1100px] grid-cols-7 gap-3">
          {STATUSES.map((status) => {
            const items = rows.filter((row) => row.status === status.id)
            return (
              <Column
                key={status.id}
                id={status.id}
                label={status.label}
                count={items.length}
              >
                {items.slice(0, PER_COLUMN).map((row) => (
                  <Card key={row.id} row={row} onOpen={onOpen} disabled={readOnly} />
                ))}
                {items.length > PER_COLUMN && (
                  <p className="px-1 text-xs text-tan">
                    +{items.length - PER_COLUMN} more in the table
                  </p>
                )}
              </Column>
            )
          })}
        </div>
      </div>
    </DndContext>
  )
}

function Column({
  id,
  label,
  count,
  children,
}: {
  id: Status
  label: string
  count: number
  children: React.ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <section
      ref={setNodeRef}
      className={cn(
        'flex min-h-[60vh] flex-col rounded-2xl border border-line bg-raised/70 p-2 transition-colors',
        isOver && 'border-ember/60 bg-raised-2/80',
      )}
    >
      <header className="flex items-center justify-between px-1.5 pt-1 pb-2">
        <span className="flex items-center gap-2 font-mono text-[11px] tracking-wide text-tan uppercase">
          <span className={cn('size-2 rounded-full', accents[id])} />
          {label}
        </span>
        <span className="font-mono text-[11px] text-tan/70">{count}</span>
      </header>
      <div className="grid gap-2">{children}</div>
    </section>
  )
}

function Card({
  row,
  onOpen,
  disabled,
}: {
  row: Application
  onOpen: (row: Application) => void
  disabled: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: row.id,
    disabled,
  })
  const age = daysSince(row.last_status_at)
  return (
    <button
      ref={setNodeRef}
      type="button"
      style={{ transform: CSS.Translate.toString(transform) }}
      onClick={() => onOpen(row)}
      className={cn(
        'w-full rounded-xl border border-line bg-raised-2 p-3 text-left text-sm transition-shadow',
        'hover:border-tan/40 focus-visible:border-ember focus-visible:outline-none',
        isDragging && 'relative z-10 shadow-xl shadow-black/40',
      )}
      {...attributes}
      {...listeners}
    >
      <p className="truncate font-medium text-cream">{row.company}</p>
      <p className="truncate text-tan">{row.role}</p>
      <p className="mt-2 flex justify-between font-mono text-[10px] text-tan/70">
        <span className="truncate">{row.source ?? ''}</span>
        <span>{age === 0 ? 'today' : `${age}d`}</span>
      </p>
    </button>
  )
}
