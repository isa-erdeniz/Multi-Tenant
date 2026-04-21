import * as React from 'react'

import { cn } from '@/lib/utils'

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'flex min-h-[140px] w-full rounded-sm border border-white/10 bg-black/30 px-4 py-3 text-lg leading-tight text-white/90 placeholder:text-white/35 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[rgba(255,107,0,0.55)] md:min-h-[180px] md:text-2xl',
          className,
        )}
        {...props}
      />
    )
  },
)
Textarea.displayName = 'Textarea'

export { Textarea }

