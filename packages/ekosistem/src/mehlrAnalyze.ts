export type MehlrAnalyzeSuccess = {
  status: 'success'
  response: string
  tokens_used?: number
}

export type MehlrAnalyzeError = {
  status: 'error'
  message: string
}

export type MehlrAnalyzeResult = MehlrAnalyzeSuccess | MehlrAnalyzeError

export async function mehlrAnalyze(
  project: string,
  params: { prompt: string; context?: Record<string, unknown> },
  analyzePath = '/mehlr/api/analyze/',
): Promise<MehlrAnalyzeResult> {
  const body = {
    project,
    prompt: params.prompt,
    context: params.context ?? {},
  }

  const res = await fetch(analyzePath, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = (await res.json()) as MehlrAnalyzeResult & Record<string, unknown>

  if (!res.ok) {
    const msg =
      typeof data.message === 'string'
        ? data.message
        : `İstek başarısız (${res.status})`
    return { status: 'error', message: msg }
  }

  if (data.status === 'success' && typeof data.response === 'string') {
    return {
      status: 'success',
      response: data.response,
      tokens_used:
        typeof data.tokens_used === 'number' ? data.tokens_used : undefined,
    }
  }

  return {
    status: 'error',
    message: typeof data.message === 'string' ? data.message : 'Beklenmeyen yanıt',
  }
}
