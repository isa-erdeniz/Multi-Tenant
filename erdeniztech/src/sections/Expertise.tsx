import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const items = [
  { title: 'SaaS', text: 'Çok kiracılı yapı, faturalama, API. Ölçek için temel.' },
  { title: 'Entegrasyon', text: 'Modeller ve veri hatları; kontrollü, denetlenebilir bağlantılar.' },
  { title: 'Güvenlik', text: 'Politika ve sertleştirme; üretimde kalıcı çerçeve.' },
]

export function Expertise() {
  return (
    <section id="hizmetler" className="relative z-10 py-16">
      <div className="mx-auto max-w-[1040px] px-5">
        <div className="mb-10 flex flex-col items-center gap-2 text-center" data-reveal>
          <h2 className="text-lg font-medium leading-none tracking-[0.28em] text-slate-400 md:text-xl">EXPERTISE</h2>
          <p className="max-w-[36ch] text-xl leading-tight text-slate-400 md:text-2xl">
            Ürün mimarisi, güvenlik ve operasyonel süreklilik — tek elden.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {items.map((it, idx) => (
            <Card
              key={it.title}
              className="group relative overflow-hidden"
              data-reveal
              data-reveal-delay={(idx * 0.08).toFixed(2)}
            >
              <div className="lava-line" />
              <CardHeader>
                <CardTitle className="text-center text-4xl font-semibold uppercase tracking-tighter text-[#FF6B00] md:text-5xl">
                  {it.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-center text-xl leading-tight text-slate-400 md:text-2xl">{it.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

