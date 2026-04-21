import { useCustomCursor } from '@/hooks/useCustomCursor'
import { cn } from '@/lib/utils'

export function CustomCursor() {
  const { x, y, hovering } = useCustomCursor()

  return (
    <>
      <div
        aria-hidden
        className={cn(
          'pointer-events-none fixed left-0 top-0 z-[9999] hidden h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[rgba(255,107,0,0.6)] mix-blend-difference transition-[transform,width,height,border-color,background-color] duration-300 md:block',
          hovering && 'h-12 w-12 border-[rgba(255,77,77,0.8)] bg-[rgba(255,77,77,0.05)]',
        )}
        style={{ transform: `translate(${x}px, ${y}px) translate(-50%, -50%)` }}
      />
      <div
        aria-hidden
        className="pointer-events-none fixed left-0 top-0 z-[10000] hidden h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[rgba(255,107,0,0.85)] md:block"
        style={{ transform: `translate(${x}px, ${y}px) translate(-50%, -50%)` }}
      />
    </>
  )
}

