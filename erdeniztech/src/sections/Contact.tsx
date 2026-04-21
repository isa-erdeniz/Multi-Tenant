import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

export function Contact() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')

  const mailto = useMemo(() => {
    const subject = encodeURIComponent(`Brief — ${name || 'ErdenizTech'}`)
    const body = encodeURIComponent([`Ad Soyad: ${name}`, `E-posta: ${email}`, '', message].join('\n'))
    return `mailto:info@erdeniztech.com?subject=${subject}&body=${body}`
  }, [name, email, message])

  return (
    <section id="iletisim" className="relative z-10 py-16">
      <div className="mx-auto max-w-[1040px] px-5">
        <div className="mb-10 flex flex-col items-center gap-2 text-center" data-reveal>
          <h2 className="text-lg font-medium leading-none tracking-[0.28em] text-white/50 md:text-xl">CONTACT</h2>
          <p className="max-w-[36ch] text-xl leading-tight text-[#888] md:text-2xl">Brief ve iş birliği.</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card className="group relative overflow-hidden p-8" data-reveal data-reveal-from="-x">
            <div className="lava-line" />
            <CardHeader className="p-0">
              <CardTitle className="text-4xl font-semibold leading-none tracking-wide text-white/95 normal-case md:text-5xl">İsa Erdeniz</CardTitle>
            </CardHeader>
            <CardContent className="p-0 pt-3">
              <p className="text-xl leading-tight text-[#888] md:text-2xl">Founder</p>
              <p className="mt-4 text-lg leading-tight text-[#888] md:text-2xl">+90 5xx xxx xx xx</p>
            </CardContent>
          </Card>

          <Card className="group relative overflow-hidden p-8" data-reveal data-reveal-from="x">
            <div className="lava-line" />
            <CardHeader className="p-0">
              <CardTitle>Mesaj</CardTitle>
            </CardHeader>
            <CardContent className="p-0 pt-4">
              <form
                className="mx-auto grid max-w-[520px] gap-4 text-center"
                onSubmit={(e) => {
                  e.preventDefault()
                  window.location.href = mailto
                }}
              >
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ad Soyad" required />
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-posta" required />
                <Textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Mesaj" rows={4} required />
                <Button type="submit" variant="lava" className="w-full text-lg">
                  Gönder
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  )
}

