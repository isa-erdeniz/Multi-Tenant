export function Footer() {
  return (
    <footer className="relative z-10 border-t border-white/10 py-10">
      <div className="mx-auto grid max-w-[1040px] gap-6 px-5 md:grid-cols-[1.2fr_.8fr_.8fr]">
        <div className="text-center md:text-left" data-reveal>
          <div className="flex items-center justify-center gap-3 md:justify-start">
            <div className="grid h-11 w-11 place-items-center rounded-xl border border-[#FF6B00]/35 bg-[#FF6B00]/10 text-2xl leading-none text-[#FF6B00]">
              E
            </div>
            <div>
              <div className="text-2xl leading-none text-[#FF6B00] md:text-3xl">ErdenizTech</div>
              <div className="mt-1 text-base font-medium leading-none tracking-[0.2em] text-[#FF6B00]/85 uppercase md:text-lg">
                Silent delivery
              </div>
            </div>
          </div>
          <p className="mt-4 text-lg leading-tight text-[#FF6B00]/80 transition-colors hover:text-[#ffa366] md:text-2xl">
            Ölçülebilir ürün. Sessiz teslim.
          </p>
        </div>

        <div className="text-center" data-reveal data-reveal-delay="0.06">
          <div className="mb-4 text-base font-semibold leading-none tracking-[0.2em] text-[#FF6B00] uppercase md:text-lg">Link</div>
          <div className="grid gap-3 text-lg leading-none tracking-[0.12em] text-[#FF6B00] uppercase">
            <a className="transition-colors duration-300 hover:text-[#ffa366]" href="#hizmetler">
              Expertise
            </a>
            <a className="transition-colors duration-300 hover:text-[#ffa366]" href="#markalar">
              Ecosystem
            </a>
            <a className="transition-colors duration-300 hover:text-[#ffa366]" href="#iletisim">
              Contact
            </a>
          </div>
        </div>

        <div className="text-center" data-reveal data-reveal-delay="0.12">
          <div className="mb-4 text-base font-semibold leading-none tracking-[0.2em] text-[#FF6B00] uppercase md:text-lg">Yasal</div>
          <div className="grid gap-3 text-lg leading-none text-[#FF6B00] md:text-2xl">
            <span className="transition-colors hover:text-[#ffa366]">KVKK</span>
            <span className="transition-colors hover:text-[#ffa366]">Koşullar</span>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-8 flex max-w-[1040px] justify-center px-5 text-lg leading-none text-[#FF6B00] transition-colors hover:text-[#ffa366] md:text-2xl">
        © 2026 ErdenizTech
      </div>
    </footer>
  )
}

