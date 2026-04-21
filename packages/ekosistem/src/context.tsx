import { createContext, useContext, type ReactNode } from 'react'

export type EcosystemConfig = {
  /** Registry / garment_core tenant slug */
  tenantSlug: string
  /** MEHLR `project` alanı (PROJECT_PROMPTS / seed) */
  mehlrProject: string
  /** Varsayılan: /mehlr/api/analyze/ */
  analyzePath?: string
}

const EcosystemContext = createContext<EcosystemConfig | null>(null)

export function EcosystemProvider({
  value,
  children,
}: {
  value: EcosystemConfig
  children: ReactNode
}) {
  return (
    <EcosystemContext.Provider value={value}>{children}</EcosystemContext.Provider>
  )
}

export function useEcosystem(): EcosystemConfig {
  const ctx = useContext(EcosystemContext)
  if (!ctx) {
    throw new Error('@erdeniztech/ekosistem: EcosystemProvider eksik')
  }
  return ctx
}
