export const MODELS = [
  'gemini-2.5-flash-lite',
  'gemini-2.5-flash',
  'gemini-2.5-pro',
  'gemini-2.0-flash',
  'gemini-2.0-flash-lite',
] as const

export const FREE_TIER: Record<string, { rpd: number; rpm: number }> = {
  'gemini-2.5-flash-lite': { rpd: 1500, rpm: 30 },
  'gemini-2.5-flash':      { rpd: 500,  rpm: 10 },
  'gemini-2.5-pro':        { rpd: 25,   rpm: 5  },
  'gemini-2.0-flash':      { rpd: 1500, rpm: 15 },
  'gemini-2.0-flash-lite': { rpd: 1500, rpm: 30 },
}

export const MODEL_FALLBACK_ORDER = [
  'gemini-2.5-flash-lite',
  'gemini-2.0-flash',
  'gemini-2.0-flash-lite',
  'gemini-2.5-flash',
  'gemini-2.5-pro',
]

export function nextFallbackModel(current: string): string {
  const idx = MODEL_FALLBACK_ORDER.indexOf(current)
  if (idx === -1) return MODEL_FALLBACK_ORDER[0]
  return MODEL_FALLBACK_ORDER[(idx + 1) % MODEL_FALLBACK_ORDER.length]
}

export function secondsUntilMidnightUTC(): number {
  const now = new Date()
  const midnight = new Date(Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate() + 1,
  ))
  return Math.max(0, Math.floor((midnight.getTime() - now.getTime()) / 1000))
}

export function fmtDuration(s: number): string {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${h}h ${m}m ${sec}s`
}
