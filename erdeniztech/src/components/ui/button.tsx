import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm text-lg font-medium leading-none tracking-[0.15em] uppercase transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[rgba(255,107,0,0.55)] disabled:pointer-events-none disabled:opacity-50 md:text-2xl',
  {
    variants: {
      variant: {
        default:
          'border border-white/10 bg-transparent text-white/85 hover:border-white/25 hover:bg-white/5 hover:text-white',
        lava: [
          'relative overflow-hidden border border-[#FF6B00] bg-[#FF6B00] text-white',
          'before:content-[\'\'] before:pointer-events-none before:absolute before:inset-0 before:-translate-x-full before:bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.18),transparent)] before:transition-transform before:duration-700 hover:before:translate-x-full',
          'hover:border-[#ff8533] hover:bg-[#ff8533]',
          'hover:shadow-[0_0_32px_rgba(139,92,246,0.55),0_0_64px_rgba(167,139,250,0.28),0_12px_32px_rgba(249,115,22,0.2)]',
          'hover:-translate-y-[2px]',
        ].join(' '),
      },
      size: {
        default: 'h-14 px-6 py-4',
        sm: 'h-12 px-5',
        lg: 'h-16 px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props}>
        {children}
      </Comp>
    )
  },
)
Button.displayName = 'Button'

export { Button }

