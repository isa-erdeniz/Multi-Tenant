import * as React from 'react'

import { cn } from '@/lib/utils'

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<'input'>>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        'flex h-14 w-full rounded-sm border border-white/10 bg-black/30 px-4 py-3 text-lg leading-none text-white/90 placeholder:text-white/35 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[rgba(255,107,0,0.55)] md:h-16 md:text-2xl',
        className,
      )}
      {...props}
    />
  )
})
Input.displayName = 'Input'

export { Input }

