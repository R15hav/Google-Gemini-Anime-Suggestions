export interface Recommendation {
  title: string
  reason: string
  match_score: number
  similar: string
  year: number | null
  studio: string
  genres: string[]
}

export interface UserProfile {
  username: string
  watched: number
  mean_score: number
  top_genres: string[]
  recent_fav: string
}

export interface RecommendationResponse {
  series: Recommendation[]
  movies: Recommendation[]
  games: Recommendation[]
  notes: string
  thinking: string
  profile: UserProfile
}

export interface ValidationResult {
  status: 'ok' | 'error' | 'warn' | 'anilist' | 'backend'
  message: string
}

export interface QuotaError {
  model: string
  ts: number
}
