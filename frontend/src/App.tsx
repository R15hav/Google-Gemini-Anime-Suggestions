import { useState } from 'react'
import { getRecommendations } from './api'
import type { ApiError } from './api'
import { ErrorBanner } from './components/ErrorBanner'
import { Hero } from './components/Hero'
import { NotesCard } from './components/NotesCard'
import { RecommendationCard } from './components/RecommendationCard'
import { SettingsModal } from './components/SettingsModal'
import { StatusChips } from './components/StatusChips'
import { ThinkingPanel } from './components/ThinkingPanel'
import { nextFallbackModel } from './constants'
import { useLocalStorage } from './hooks/useLocalStorage'
import type { QuotaError, RecommendationResponse, ValidationResult } from './types'

export default function App() {
  const [apiKey, setApiKey] = useLocalStorage<string>('animeSenseiGeminiKey', '')
  const [username, setUsername] = useState('')
  const [model, setModel] = useState('gemini-2.5-flash-lite')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [quotaError, setQuotaError] = useState<QuotaError | null>(null)
  const [bannerError, setBannerError] = useState<{ type: 'quota' | 'auth' | 'error'; message: string } | null>(null)

  const profileOk = validationResult?.status === 'ok'
  const canFetch = !!apiKey && profileOk

  async function handleGetRecs() {
    setResult(null)
    setBannerError(null)
    setLoading(true)
    try {
      const data = await getRecommendations(username, model, apiKey)
      setResult(data)
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
          background: canFetch && !loading ? 'var(--accent)' : 'var(--border)',
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

      {/* Results */}
      {result && (
        <section style={{ marginTop: '2rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <p style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--muted-2)', marginBottom: '4px' }}>
              For {username}
            </p>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--ink)' }}>
              Your Picks
            </h2>
          </div>

          {/* Profile notes */}
          {result.notes && <NotesCard notes={result.notes} />}

          {/* Thinking process (collapsible) */}
          {result.thinking && <ThinkingPanel thinking={result.thinking} />}

          {/* Series section */}
          {result.series.length > 0 && (
            <div style={{ marginBottom: '2rem' }}>
              <SectionHeading icon="📺" label="Anime Series" count={result.series.length} />
              {result.series.map((rec, i) => (
                <RecommendationCard key={rec.title} rec={rec} index={i} />
              ))}
            </div>
          )}

          {/* Movies section */}
          {result.movies.length > 0 && (
            <div>
              <SectionHeading icon="🎬" label="Anime Movies" count={result.movies.length} />
              {result.movies.map((rec, i) => (
                <RecommendationCard key={rec.title} rec={rec} index={i} />
              ))}
            </div>
          )}
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

function SectionHeading({ icon, label, count }: { icon: string; label: string; count: number }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      marginBottom: '1rem',
      paddingBottom: '0.6rem',
      borderBottom: '2px solid var(--accent)',
    }}>
      <span style={{ fontSize: '1.1rem' }}>{icon}</span>
      <h3 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '1.15rem',
        fontWeight: 700,
        color: 'var(--ink)',
        margin: 0,
      }}>
        {label}
      </h3>
      <span style={{
        marginLeft: 'auto',
        fontSize: '0.73rem',
        fontWeight: 600,
        color: 'var(--muted-2)',
        background: 'var(--surface-2)',
        padding: '2px 10px',
        borderRadius: '99px',
        border: '1px solid var(--border)',
      }}>
        {count}
      </span>
    </div>
  )
}
