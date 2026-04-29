export interface Recommendation {
  title: string
  reason: string
  match_score: number
}

export interface ValidationResult {
  status: 'ok' | 'error' | 'warn'
  message: string
}

export interface QuotaError {
  model: string
  ts: number
}
