import { useEffect } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function useScrollReveal() {
  useEffect(() => {
    // Defensive: never break rendering if GSAP/ScrollTrigger fails
    try {
      const ctx = gsap.context(() => {
        const targets = gsap.utils.toArray<HTMLElement>('[data-reveal]')
        if (!targets.length) return

        targets.forEach((el) => {
          const from = el.dataset.revealFrom ?? 'y'
          const distance = Number(el.dataset.revealDistance ?? '40')
          const delay = Number(el.dataset.revealDelay ?? '0')

          const varsFrom =
            from === 'x'
              ? { opacity: 0, x: distance }
              : from === '-x'
                ? { opacity: 0, x: -distance }
                : { opacity: 0, y: distance }

          gsap.fromTo(el, varsFrom, {
            opacity: 1,
            x: 0,
            y: 0,
            duration: 0.8,
            delay,
            ease: 'power3.out',
            scrollTrigger: {
              trigger: el,
              start: 'top 85%',
              once: true,
            },
          })
        })
      })

      return () => ctx.revert()
    } catch {
      return
    }
  }, [])
}

