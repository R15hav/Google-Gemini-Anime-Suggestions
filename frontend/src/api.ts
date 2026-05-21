import type { RecommendationResponse } from './types'

const BASE = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? ''

export interface ValidateResponse {
  username: string
  completed_count: number
}

export interface ApiError {
  detail: string
  status: number
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json() as Promise<T>
  let detail = `HTTP ${res.status}`
  try {
    const body = await res.json() as { detail?: string }
    if (body.detail) detail = body.detail
  } catch { /* ignore */ }
  const err: ApiError = { detail, status: res.status }
  throw err
}

export async function validateUser(username: string): Promise<ValidateResponse> {
  const res = await fetch(`${BASE}/validate/${encodeURIComponent(username)}`)
  return handleResponse<ValidateResponse>(res)
}

export async function getRecommendations(
  username: string,
  model: string,
  apiKey: string,
): Promise<RecommendationResponse> {
  const url = `${BASE}/recommend/${encodeURIComponent(username)}?model_choice=${encodeURIComponent(model)}`
  const res = await fetch(url, {
    headers: { 'x-gemini-api-key': apiKey },
  })
  return handleResponse<RecommendationResponse>(res)
}

export interface StreamHandlers {
  onStatus?: (text: string) => void
  onChunk?: (text: string) => void
}

export async function getRecommendationsStream(
  username: string,
  model: string,
  apiKey: string,
  handlers: StreamHandlers,
): Promise<RecommendationResponse> {
  const url = `${BASE}/recommend-stream/${encodeURIComponent(username)}?model_choice=${encodeURIComponent(model)}`
  const res = await fetch(url, { headers: { 'x-gemini-api-key': apiKey } })

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json() as { detail?: string }
      if (body.detail) detail = body.detail
    } catch { /* ignore */ }
    throw { detail, status: res.status } as ApiError
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: RecommendationResponse | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let nl: number
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim()
      buffer = buffer.slice(nl + 1)
      if (!line) continue

      let evt: { type: string; text?: string; result?: RecommendationResponse; detail?: string; status?: number }
      try { evt = JSON.parse(line) } catch { continue }

      if (evt.type === 'status' && evt.text) handlers.onStatus?.(evt.text)
      else if (evt.type === 'chunk' && evt.text) handlers.onChunk?.(evt.text)
      else if (evt.type === 'done' && evt.result) finalResult = evt.result
      else if (evt.type === 'error') throw { detail: evt.detail ?? 'Unknown error', status: evt.status ?? 500 } as ApiError
    }
  }

  if (!finalResult) throw { detail: 'Stream ended without a final result.', status: 502 } as ApiError
  return finalResult
}
