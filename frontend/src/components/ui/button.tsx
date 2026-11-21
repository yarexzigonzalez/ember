import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import type { ButtonHTMLAttributes } from 'react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-full whitespace-nowrap px-4 py-2 text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-ember text-ink hover:bg-ember-2',
        quiet: 'border border-line bg-raised text-cream hover:border-tan/40',
        ghost: 'text-cream hover:bg-raised-2',
        danger: 'bg-oxblood text-cream hover:bg-oxblood/80',
      },
      size: {
        md: 'h-10 px-4',
        sm: 'h-8 px-3 text-xs',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }

export function Button({ className, variant, size, asChild, type, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return (
    <Comp
      className={cn(buttonVariants({ variant, size }), className)}
      type={asChild ? undefined : (type ?? 'button')}
      {...props}
    />
  )
}
