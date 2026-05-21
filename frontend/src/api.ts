import type { RecommendationResponse } from './types'

const BASE = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? ''

export interface ValidateResponse {
  username: string
  completed_count: number
}

export interface ApiError {
  detail: string
  status: number
  quotaMetric?: string
  quotaLimit?: number
  retryAfterSeconds?: number
  billedModel?: string
  modelFromApi?: string
}

interface StructuredQuotaDetail {
  message?: string
  metric?: string
  limit?: number
  model?: string
  model_from_api?: string
  retry_after_seconds?: number
  billed_model?: string
}

function quotaFieldsFromDetail(detail: unknown): Partial<ApiError> {
  if (detail && typeof detail === 'object') {
    const d = detail as StructuredQuotaDetail
    return {
      quotaMetric: d.metric,
      quotaLimit: d.limit,
      retryAfterSeconds: d.retry_after_seconds,
      billedModel: d.billed_model,
      modelFromApi: d.model_from_api,
    }
  }
  return {}
}

async function handleResponse<T>(res: Response): Promise<T> {
  const billedHeader = res.headers.get('x-billed-model') ?? undefined
  if (res.ok) return res.json() as Promise<T>

  let detail = `HTTP ${res.status}`
  let quotaFields: Partial<ApiError> = {}
  try {
    const body = await res.json() as { detail?: string | StructuredQuotaDetail }
    if (typeof body.detail === 'string') {
      detail = body.detail
    } else if (body.detail && typeof body.detail === 'object') {
      const d = body.detail
      detail = d.message ?? detail
      quotaFields = quotaFieldsFromDetail(d)
    }
  } catch { /* ignore */ }

  const err: ApiError = { detail, status: res.status, ...quotaFields }
  if (billedHeader && !err.billedModel) err.billedModel = billedHeader
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
  onBilled?: (model: string) => void,
): Promise<RecommendationResponse> {
  const url = `${BASE}/recommend/${encodeURIComponent(username)}?model_choice=${encodeURIComponent(model)}`
  const res = await fetch(url, {
    headers: { 'x-gemini-api-key': apiKey },
  })
  const billed = res.headers.get('x-billed-model')
  if (billed && onBilled) onBilled(billed)
  return handleResponse<RecommendationResponse>(res)
}

export interface StreamHandlers {
  onStatus?: (text: string) => void
  onChunk?: (text: string) => void
  onBilled?: (model: string) => void
}

interface StreamEvent {
  type: string
  text?: string
  result?: RecommendationResponse
  detail?: string
  status?: number
  model?: string
  model_from_api?: string
  metric?: string
  limit?: number
  retry_after_seconds?: number
  billed_model?: string
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
  const billedOnce = new Set<string>()

  const fireBilled = (m: string | undefined) => {
    if (!m || billedOnce.has(m)) return
    billedOnce.add(m)
    handlers.onBilled?.(m)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let nl: number
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim()
      buffer = buffer.slice(nl + 1)
      if (!line) continue

      let evt: StreamEvent
      try { evt = JSON.parse(line) } catch { continue }

      if (evt.type === 'status' && evt.text) {
        handlers.onStatus?.(evt.text)
      } else if (evt.type === 'chunk' && evt.text) {
        handlers.onChunk?.(evt.text)
      } else if (evt.type === 'billed') {
        fireBilled(evt.model)
      } else if (evt.type === 'done' && evt.result) {
        fireBilled(evt.billed_model)
        finalResult = evt.result
      } else if (evt.type === 'error') {
        fireBilled(evt.billed_model)
        const err: ApiError = {
          detail: evt.detail ?? 'Unknown error',
          status: evt.status ?? 500,
          quotaMetric: evt.metric,
          quotaLimit: evt.limit,
          retryAfterSeconds: evt.retry_after_seconds,
          billedModel: evt.billed_model,
          modelFromApi: evt.model_from_api,
        }
        throw err
      }
    }
  }

  if (!finalResult) throw { detail: 'Stream ended without a final result.', status: 502 } as ApiError
  return finalResult
}
