import { Button } from '@/components/ui/button'

export function Header() {
  return (
    <div className="sticky top-0 z-50 border-b border-white/10 bg-black/40 backdrop-blur-xl">
      <header className="mx-auto flex max-w-[1040px] flex-wrap items-center justify-between gap-4 px-5 py-4">
        <a href="#top" className="flex items-center gap-3 font-semibold tracking-wide" data-cursor="hover">
          <div className="grid h-11 w-11 place-items-center rounded-xl border border-white/10 bg-white/5 text-2xl leading-none text-white/80">
            E
          </div>
          <div className="relative">
            <span
              className="pointer-events-none absolute -inset-2 rounded-lg bg-violet-500/15 blur-xl md:-inset-3"
              aria-hidden
            />
            <div className="relative text-2xl leading-none text-white md:text-3xl">ErdenizTech</div>
            <div className="relative mt-1 text-base font-medium leading-none tracking-[0.2em] text-slate-400 md:text-lg">Product · Systems</div>
          </div>
        </a>

        <nav className="hidden items-center gap-7 text-lg font-medium leading-none tracking-[0.18em] text-[#FF6B00] md:flex">
          <a href="#hizmetler" className="transition-colors duration-300 hover:text-[#ffa366]">
            Expertise
          </a>
          <a href="#markalar" className="transition-colors duration-300 hover:text-[#ffa366]">
            Ecosystem
          </a>
          <a href="#iletisim" className="transition-colors duration-300 hover:text-[#ffa366]">
            Contact
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Button asChild variant="lava">
            <a href="#markalar">Ecosystem</a>
          </Button>
          <Button asChild variant="lava">
            <a href="#iletisim">Brief</a>
          </Button>
        </div>
      </header>
    </div>
  )
}

