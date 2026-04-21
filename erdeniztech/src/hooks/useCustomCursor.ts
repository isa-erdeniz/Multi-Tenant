import { useEffect, useMemo, useState } from 'react'

type CursorState = {
  x: number
  y: number
  hovering: boolean
}

export function useCustomCursor() {
  const [state, setState] = useState<CursorState>({ x: -100, y: -100, hovering: false })

  const selectors = useMemo(() => ['a', 'button', '[data-cursor="hover"]', '.glass-card'], [])

  useEffect(() => {
    const onMove = (e: MouseEvent) => setState((s) => ({ ...s, x: e.clientX, y: e.clientY }))

    const isInteractive = (el: Element | null) => {
      if (!el) return false
      return selectors.some((sel) => (el as HTMLElement).closest(sel))
    }

    const onOver = (e: MouseEvent) => {
      const target = e.target as Element | null
      if (!target) return
      setState((s) => ({ ...s, hovering: isInteractive(target) }))
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('mouseover', onOver, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
    }
  }, [selectors])

  return state
}

