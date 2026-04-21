import { useEffect } from 'react'
import Lenis from 'lenis'

export function useSmoothScroll() {
  useEffect(() => {
    // Defensive: never break rendering if Lenis fails
    let lenis: Lenis | null = null
    try {
      lenis = new Lenis({
        lerp: 0.08,
        wheelMultiplier: 0.95,
        touchMultiplier: 1.15,
        smoothWheel: true,
      })
    } catch {
      return
    }

    let raf = 0
    const loop = (time: number) => {
      lenis?.raf(time)
      raf = requestAnimationFrame(loop)
    }

    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      lenis?.destroy()
    }
  }, [])
}

