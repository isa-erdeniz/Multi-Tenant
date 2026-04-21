import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

type EcosystemBrand = {
  name: string
  description: string
  url: string
  featured?: boolean
  badge?: string
}

const ecosystem: EcosystemBrand[] = [
  { name: 'Dressifye', description: 'Moda denemesi ve ürün yüzeyi. Odak: hız ve netlik.', url: 'https://dressifye.com', featured: true },
  { name: 'StyleCoree', description: 'Stil verisi; sakin arayüz, okunaklı hiyerarşi.', url: 'https://stylecoree.com', badge: 'YENİ' },
  { name: 'StyleForHuman', description: 'Görünüm kararları; sade etkileşim katmanı.', url: 'https://styleforhuman.com' },
  { name: 'HairInfinitye', description: 'Bakım yolculuğu; güvenilir temas noktaları.', url: 'https://hairinfinitye.com', badge: 'KEŞFEDİN' },
]

const labs = [
  { title: 'Eğitim', description: 'Akış, içerik, ölçüm.' },
  { title: 'Operasyon', description: 'Saha ve ekip görünürlüğü.' },
  { title: 'IoT', description: 'Cihaz ve süreç otomasyonu.' },
]

export function Ecosystem() {
  const featured = ecosystem.find((x) => x.featured) ?? ecosystem[0]
  const rest = ecosystem.filter((x) => x !== featured)

  return (
    <section id="markalar" className="relative z-10 py-16">
      <div className="mx-auto max-w-[1040px] px-5">
        <div className="mb-10 flex flex-col items-center gap-2 text-center" data-reveal>
          <h2 className="text-lg font-medium leading-none tracking-[0.28em] text-white/50 md:text-xl">ECOSYSTEM</h2>
          <p className="max-w-[36ch] text-xl font-bold leading-tight text-white md:text-2xl">Dört yüzey. Aynı disiplin.</p>
        </div>

        {/* Featured (Dressifye) */}
        <div className="mb-8" data-reveal>
          <div className="relative mx-auto w-full max-w-[920px]">
            <span
              className="pointer-events-none absolute -right-3 -top-3 z-20 animate-badge-float rounded-md border border-orange-500/30 bg-black/45 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-white/90 shadow-[0_8px_24px_rgba(0,0,0,0.35)] backdrop-blur-sm"
              aria-hidden
            >
              MERKEZİ EKOSİSTEM
            </span>
            <Card className="group relative flex min-h-[340px] flex-col overflow-hidden p-10 text-center">
              <div className="lava-line" />

              <div className="flex flex-1 flex-col items-center justify-between py-2">
                <div className="w-full">
                  <h3 className="mb-5 whitespace-nowrap text-4xl font-semibold leading-none tracking-tighter text-[#ff6b00] md:text-6xl">
                    {featured.name}
                  </h3>
                  <p className="mx-auto max-w-[42ch] text-lg leading-tight text-[#d1d5db] md:text-2xl">
                    {featured.description}
                  </p>
                </div>

                <Button asChild variant="lava" className="mt-8 w-full max-w-[420px] text-lg md:text-2xl">
                  <a href={featured.url} target="_blank" rel="noopener noreferrer">
                    Web sitesini ziyaret et
                  </a>
                </Button>
              </div>

              <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100">
                <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,77,77,0.06),transparent,rgba(249,115,22,0.06))]" />
              </div>
            </Card>
          </div>
        </div>

        {/* Other 3 cards */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {rest.map((it, idx) => (
            <div key={it.name} className="relative" data-reveal data-reveal-delay={(idx * 0.08).toFixed(2)}>
              {it.badge ? (
                <span
                  className="pointer-events-none absolute -right-3 -top-3 z-20 animate-badge-float rounded-md border border-orange-500/30 bg-black/45 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-white/90 shadow-[0_8px_24px_rgba(0,0,0,0.35)] backdrop-blur-sm"
                  style={{ animationDelay: `${idx * 0.35}s` }}
                  aria-hidden
                >
                  {it.badge}
                </span>
              ) : null}
              <Card className="group relative flex min-h-[320px] flex-col overflow-hidden p-8 text-center">
                <div className="lava-line" />

                <div className="flex flex-1 flex-col items-center justify-between py-2">
                  <div className="w-full">
                    <h3 className="mb-4 whitespace-nowrap text-2xl font-semibold leading-none tracking-tighter text-[#ff6b00] md:text-3xl">
                      {it.name}
                    </h3>
                    <p className="mx-auto max-w-[28ch] text-lg leading-tight text-[#d1d5db] md:text-2xl">{it.description}</p>
                  </div>

                  <Button asChild variant="lava" className="mt-6 w-full max-w-[320px] text-lg md:text-2xl">
                    <a href={it.url} target="_blank" rel="noopener noreferrer">
                      Keşfet
                    </a>
                  </Button>
                </div>

                <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100">
                  <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,77,77,0.05),transparent,rgba(249,115,22,0.05))]" />
                </div>
              </Card>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <h3 className="text-base font-medium leading-none tracking-[0.26em] text-white/40 uppercase md:text-lg" data-reveal>
            Innovation Labs
          </h3>
          <p className="mx-auto mt-3 max-w-[40ch] text-lg leading-tight text-[#d1d5db] md:text-2xl" data-reveal data-reveal-delay="0.08">
            İsim paylaşılmadan; tamamlayıcı hatlar.
          </p>
        </div>

        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          {labs.map((lab, idx) => (
            <Card key={lab.title} className="group relative overflow-hidden p-5" data-reveal data-reveal-delay={(0.12 + idx * 0.06).toFixed(2)}>
              <div className="lava-line" />
              <div className="mb-2 flex items-center justify-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-[#f97316]" />
                <h4 className="text-2xl font-semibold leading-none tracking-[0.14em] text-white/55 uppercase md:text-3xl">{lab.title}</h4>
              </div>
              <p className="text-center text-lg leading-tight text-[#d1d5db] md:text-2xl">{lab.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

