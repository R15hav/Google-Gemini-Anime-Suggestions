import type { Recommendation } from './types'

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
): Promise<Recommendation[]> {
  const url = `${BASE}/recommend/${encodeURIComponent(username)}?model_choice=${encodeURIComponent(model)}`
  const res = await fetch(url, {
    headers: { 'x-gemini-api-key': apiKey },
  })
  return handleResponse<Recommendation[]>(res)
}
