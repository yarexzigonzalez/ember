import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

export function Dialog({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children: ReactNode
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/60" />
        <DialogPrimitive.Content className="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-[min(560px,calc(100%-1.5rem))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-line bg-raised p-5 shadow-2xl">
          <div className="mb-4 flex items-start justify-between gap-4">
            <DialogPrimitive.Title className="font-serif text-2xl text-cream">
              {title}
            </DialogPrimitive.Title>
            <DialogPrimitive.Close className="rounded-full p-1 text-tan hover:bg-raised-2 hover:text-cream">
              <X size={16} />
            </DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
