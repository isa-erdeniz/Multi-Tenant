import { useCallback, useId, useState } from 'react'
import { useEcosystem } from './context'
import { mehlrAnalyze } from './mehlrAnalyze'

const MAX_PROMPT = 4000

export function AiAssistPanel() {
  const { mehlrProject, analyzePath } = useEcosystem()
  const panelId = useId()
  const [open, setOpen] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = useCallback(async () => {
    const trimmed = prompt.trim()
    if (!trimmed) {
      setError('Lütfen bir soru veya istek yazın.')
      return
    }
    setLoading(true)
    setError('')
    setAnswer('')
    try {
      const ctx = {
        page_title: document.title,
        path: window.location.pathname,
        href: window.location.href,
      }
      const out = await mehlrAnalyze(
        mehlrProject,
        { prompt: trimmed, context: ctx },
        analyzePath ?? '/mehlr/api/analyze/',
      )
      if (out.status === 'success') {
        setAnswer(out.response)
      } else {
        setError(out.message)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Bağlantı hatası'
      setError(
        msg.includes('Failed to fetch')
          ? 'MEHLR erişilemiyor. Yerelde Vite proxy + MEHLR_SERVICE_API_KEY; üretimde aynı kök altında /mehlr vekili kullanın.'
          : msg,
      )
    } finally {
      setLoading(false)
    }
  }, [prompt, mehlrProject, analyzePath])

  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-[100] flex flex-col items-end gap-2">
      {open ? (
        <div
          id={panelId}
          className="pointer-events-auto w-[min(100vw-2rem,22rem)] rounded-2xl border border-white/15 bg-[#0a0a0a]/95 p-4 text-sm text-[#e8e8e8] shadow-2xl backdrop-blur-md"
          role="dialog"
          aria-label="ErdenizTech ekosistem yapay zeka asistanı"
        >
          <p className="mb-2 text-xs text-white/50">
            MEHLR — proje: <span className="text-white/70">{mehlrProject}</span>. Sayfa
            bağlamı otomatik eklenir.
          </p>
          <textarea
            className="mb-2 min-h-[88px] w-full resize-y rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-[13px] outline-none ring-0 placeholder:text-white/30 focus:border-white/25"
            placeholder="Sorunuzu yazın…"
            maxLength={MAX_PROMPT}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value.slice(0, MAX_PROMPT))}
            disabled={loading}
          />
          <div className="mb-2 flex justify-between gap-2">
            <button
              type="button"
              className="rounded-full border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"
              onClick={() => setOpen(false)}
            >
              Kapat
            </button>
            <button
              type="button"
              className="rounded-full bg-white/90 px-4 py-1.5 text-xs font-medium text-black hover:bg-white disabled:opacity-50"
              onClick={() => void run()}
              disabled={loading}
            >
              {loading ? 'Gönderiliyor…' : 'Gönder'}
            </button>
          </div>
          {error ? (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200">
              {error}
            </p>
          ) : null}
          {answer ? (
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-white/10 bg-black/30 p-2 text-xs leading-relaxed text-white/85">
              {answer}
            </pre>
          ) : null}
        </div>
      ) : null}

      <button
        type="button"
        className="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full border border-white/20 bg-gradient-to-br from-white/15 to-white/5 text-xl shadow-lg backdrop-blur-md transition hover:scale-105 hover:border-white/35"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
        title="Ekosistem AI"
      >
        ✦
      </button>
    </div>
  )
}
