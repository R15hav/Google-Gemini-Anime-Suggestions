import { useState } from 'react'
import { getRecommendations } from './api'
import type { ApiError } from './api'
import { ErrorBanner } from './components/ErrorBanner'
import { Hero } from './components/Hero'
import { RecommendationCard } from './components/RecommendationCard'
import { SettingsModal } from './components/SettingsModal'
import { StatusChips } from './components/StatusChips'
import { nextFallbackModel } from './constants'
import { useLocalStorage } from './hooks/useLocalStorage'
import type { QuotaError, Recommendation, ValidationResult } from './types'

export default function App() {
  const [apiKey, setApiKey] = useLocalStorage<string>('animeSenseiGeminiKey', '')
  const [username, setUsername] = useState('')
  const [model, setModel] = useState('gemini-2.5-flash-lite')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [quotaError, setQuotaError] = useState<QuotaError | null>(null)
  const [bannerError, setBannerError] = useState<{ type: 'quota' | 'auth' | 'error'; message: string } | null>(null)

  const profileOk = validationResult?.status === 'ok'
  const canFetch = !!apiKey && profileOk

  async function handleGetRecs() {
    setRecommendations(null)
    setBannerError(null)
    setLoading(true)
    try {
      const recs = await getRecommendations(username, model, apiKey)
      setRecommendations(recs)
      setQuotaError(null)
    } catch (e: unknown) {
      const err = e as ApiError
      if (err.status === 429) {
        setQuotaError({ model, ts: Date.now() })
        setBannerError({
          type: 'quota',
          message: `${err.detail} Try switching to ${nextFallbackModel(model)}. `,
        })
      } else if (err.status === 401) {
        setBannerError({ type: 'auth', message: err.detail })
      } else {
        setBannerError({ type: 'error', message: err.detail ?? 'Something went wrong.' })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '680px', margin: '0 auto', padding: '0 1.25rem 5rem' }}>
      <Hero />

      <StatusChips
        hasKey={!!apiKey}
        username={username}
        profileOk={profileOk}
        model={model}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* CTA button */}
      <button
        disabled={!canFetch || loading}
        onClick={handleGetRecs}
        style={{
          width: '100%',
          padding: '0.85rem',
          borderRadius: 'var(--radius-md)',
          background: canFetch && !loading
            ? 'var(--accent)'
            : 'var(--border)',
          color: canFetch && !loading ? '#fff' : 'var(--muted)',
          fontSize: '0.97rem',
          fontWeight: 600,
          letterSpacing: '0.01em',
          cursor: canFetch && !loading ? 'pointer' : 'not-allowed',
          transition: 'background 0.15s, transform 0.12s, box-shadow 0.15s',
          boxShadow: canFetch && !loading ? '0 2px 12px rgba(220,38,38,0.28)' : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          marginBottom: '1rem',
        }}
        onMouseEnter={e => {
          if (!canFetch || loading) return
          const b = e.currentTarget
          b.style.transform = 'translateY(-1px)'
          b.style.boxShadow = '0 4px 20px rgba(220,38,38,0.38)'
        }}
        onMouseLeave={e => {
          const b = e.currentTarget
          b.style.transform = 'translateY(0)'
          b.style.boxShadow = canFetch && !loading ? '0 2px 12px rgba(220,38,38,0.28)' : 'none'
        }}
      >
        {loading ? (
          <>
            <span style={{
              display: 'inline-block',
              width: '16px', height: '16px',
              border: '2px solid rgba(255,255,255,0.3)',
              borderTopColor: '#fff',
              borderRadius: '50%',
              animation: 'spin 0.7s linear infinite',
            }} />
            Reading {username}&apos;s taste…
          </>
        ) : (
          '✦ Get Recommendations'
        )}
      </button>

      {!apiKey && !username && (
        <p style={{ textAlign: 'center', fontSize: '0.82rem', color: 'var(--muted)', marginBottom: '1rem' }}>
          Tap <strong>configure ⚙</strong> above to add your Gemini API key and AniList username.
        </p>
      )}

      {bannerError && (
        <ErrorBanner type={bannerError.type} message={bannerError.message} />
      )}

      {recommendations && recommendations.length > 0 && (
        <section>
          <div style={{ textAlign: 'center', margin: '2rem 0 1.25rem' }}>
            <p style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--muted-2)', marginBottom: '4px' }}>
              For {username}
            </p>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--ink)' }}>
              Your Picks
            </h2>
          </div>
          {recommendations.map((rec, i) => (
            <RecommendationCard key={rec.title} rec={rec} index={i} />
          ))}
        </section>
      )}

      {/* Footer */}
      <footer style={{ textAlign: 'center', padding: '2.5rem 0 0.5rem', marginTop: '1rem' }}>
        <div style={{ width: '32px', height: '1px', background: 'var(--border)', margin: '0 auto 0.85rem' }} />
        <p style={{ fontSize: '0.73rem', color: 'var(--muted-2)', letterSpacing: '0.06em' }}>
          FastAPI &nbsp;·&nbsp; Google Gemini &nbsp;·&nbsp; AniList &nbsp;·&nbsp; React
        </p>
      </footer>

      {settingsOpen && (
        <SettingsModal
          apiKey={apiKey}
          username={username}
          model={model}
          quotaHitModel={quotaError?.model ?? null}
          onApiKeyChange={setApiKey}
          onUsernameChange={setUsername}
          onModelChange={setModel}
          onValidationResult={setValidationResult}
          validationResult={validationResult}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </div>
  )
}
