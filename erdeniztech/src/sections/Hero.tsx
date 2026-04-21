import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function Hero() {
  const rootRef = useRef<HTMLElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const leadRef = useRef<HTMLParagraphElement>(null)
  const actionsRef = useRef<HTMLDivElement>(null)
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Defensive: if GSAP fails for any reason, never block rendering
    try {
      const ctx = gsap.context(() => {
        const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

        if (titleRef.current) {
          tl.fromTo(titleRef.current, { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.8 })
        }
        if (leadRef.current) {
          tl.fromTo(leadRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7 }, '-=0.45')
        }
        if (actionsRef.current) {
          tl.fromTo(actionsRef.current, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6 }, '-=0.4')
        }
        if (cardRef.current) {
          tl.fromTo(cardRef.current, { opacity: 0, y: 24, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.7 }, '-=0.35')
        }
      }, rootRef)

      return () => ctx.revert()
    } catch {
      return
    }
  }, [])

  return (
    <section id="top" ref={rootRef} className="relative z-10 mx-auto max-w-[1040px] px-5 pb-6 pt-14">
      <div className="grid items-center gap-8 md:grid-cols-[1.05fr_.95fr]">
        <div className="mx-auto max-w-[52ch] text-center md:text-left" data-reveal>
          <div className="inline-flex rounded-sm border border-white/10 px-4 py-2 text-base font-medium leading-none tracking-[0.22em] text-slate-400 md:text-lg">
            Product · Systems
          </div>
          <div className="relative mt-5 inline-block w-full md:w-auto">
            <span
              className="pointer-events-none absolute left-1/2 top-1/2 h-[120%] w-[min(100%,520px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-500/25 blur-[48px] md:h-[140%] md:w-[140%] md:blur-[56px]"
              aria-hidden
            />
            <h1
              ref={titleRef}
              className="relative whitespace-nowrap text-5xl font-semibold leading-none tracking-tighter text-white md:text-7xl lg:text-8xl"
            >
              ErdenizTech
            </h1>
          </div>
          <p ref={leadRef} className="mt-5 text-xl leading-tight text-slate-400 md:text-3xl">
            Fikirden ölçeğe: az ama derin ürünler. Sessiz mühendislik, net teslim.
          </p>

          <div ref={actionsRef} className="mt-9 flex flex-wrap items-center justify-center gap-4 md:justify-start">
            <Button asChild variant="lava" size="lg">
              <a href="https://dressifye.com" target="_blank" rel="noopener noreferrer">
                Web sitesini ziyaret et
              </a>
            </Button>
            <Button asChild variant="lava" size="lg">
              <a href="#markalar">Keşfet</a>
            </Button>
          </div>
        </div>

        <div ref={cardRef} data-reveal data-reveal-from="x" data-reveal-distance="32">
          <Card className="group relative overflow-hidden">
            <div className="lava-line" />
            <CardHeader>
              <CardTitle className="text-center text-slate-400 md:text-left">Odak</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3 text-center text-lg leading-tight text-slate-400 md:text-left md:text-2xl">
                <li>SaaS</li>
                <li>Güvenlik</li>
                <li>Veri ve otomasyon</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}

