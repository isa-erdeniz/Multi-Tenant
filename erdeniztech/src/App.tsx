import { AiAssistPanel, EcosystemProvider } from '@erdeniztech/ekosistem'
import { BackgroundFX } from '@/sections/BackgroundFX'
import { Contact } from '@/sections/Contact'
import { CustomCursor } from '@/sections/CustomCursor'
import { Ecosystem } from '@/sections/Ecosystem'
import { Expertise } from '@/sections/Expertise'
import { Footer } from '@/sections/Footer'
import { Header } from '@/sections/Header'
import { Hero } from '@/sections/Hero'
import { useScrollReveal } from '@/hooks/useScrollReveal'
import { useSmoothScroll } from '@/hooks/useSmoothScroll'

export default function App() {
  useSmoothScroll()
  useScrollReveal()

  return (
    <EcosystemProvider
      value={{
        tenantSlug: 'erdeniztech',
        mehlrProject: 'erdeniztech',
        analyzePath: '/mehlr/api/analyze/',
      }}
    >
      <div className="relative min-h-dvh bg-transparent text-[#e8e8e8]">
        <BackgroundFX />
        <CustomCursor />
        <Header />
        <main className="relative z-10">
          <Hero />
          <Expertise />
          <Ecosystem />
          <Contact />
        </main>
        <Footer />
        <AiAssistPanel />
      </div>
    </EcosystemProvider>
  )
}

