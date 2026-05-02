import { useEffect, useMemo, useState } from 'react'
import { getRecommendations } from './api'
import type { ApiError } from './api'
import { FREE_TIER, MODELS } from './constants'
import { useLocalStorage } from './hooks/useLocalStorage'
import type { Recommendation, RecommendationResponse } from './types'

type Stage = 'input' | 'loading' | 'results'
type Theme = 'light' | 'dark'

// ─── Model labels + daily usage tracking ─────────────────────────────────────

const MODEL_LABELS: Record<string, string> = {
  'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
  'gemini-2.5-flash':      'Gemini 2.5 Flash',
  'gemini-2.5-pro':        'Gemini 2.5 Pro',
  'gemini-2.0-flash':      'Gemini 2.0 Flash',
  'gemini-2.0-flash-lite': 'Gemini 2.0 Flash Lite',
}

interface UsageState {
  date: string                         // YYYY-MM-DD UTC
  counts: Record<string, number>       // model → requests used today
  exceeded: Record<string, boolean>    // model → quota exceeded flag
}

function todayUTC() { return new Date().toISOString().slice(0, 10) }
function freshUsage(): UsageState { return { date: todayUTC(), counts: {}, exceeded: {} } }

// ─── Backdrop orbs ────────────────────────────────────────────────────────────

function Orb({ x, y, size, color, blur = 80, opacity = 0.55 }: {
  x: string; y: string; size: number; color: string; blur?: number; opacity?: number
}) {
  return (
    <div style={{
      position: 'absolute', left: x, top: y,
      width: size, height: size, borderRadius: '50%',
      background: color, filter: `blur(${blur}px)`, opacity,
      pointerEvents: 'none', zIndex: 0,
    }} />
  )
}

function Backdrop() {
  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
      <Orb x="-8%" y="-12%" size={520} color="var(--orb-1)" />
      <Orb x="62%" y="-18%" size={460} color="var(--orb-2)" />
      <Orb x="35%" y="65%" size={580} color="var(--orb-3)" blur={100} />
      <Orb x="-10%" y="55%" size={380} color="var(--orb-4)" />
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at center, transparent 0%, var(--bg) 85%)',
      }} />
    </div>
  )
}

// ─── SVG cover placeholder ────────────────────────────────────────────────────

function CoverPlaceholder({ label, hue = 280, h = 220 }: { label: string; hue?: number; h?: number }) {
  const id = useMemo(() => `s${Math.random().toString(36).slice(2, 8)}`, [])
  return (
    <svg viewBox={`0 0 200 ${h}`} preserveAspectRatio="none"
      style={{ width: '100%', height: h, display: 'block', borderRadius: 18 }}>
      <defs>
        <pattern id={id} width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
          <rect width="14" height="14" fill={`oklch(0.92 0.04 ${hue})`} />
          <rect width="7" height="14" fill={`oklch(0.88 0.05 ${hue})`} />
        </pattern>
      </defs>
      <rect width="200" height={h} fill={`url(#${id})`} rx="18" />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle"
        fill={`oklch(0.45 0.04 ${hue})`}
        style={{ font: '500 9px ui-monospace, monospace', letterSpacing: '0.08em' }}>
        {label}
      </text>
    </svg>
  )
}

// ─── Input screen ─────────────────────────────────────────────────────────────

function InputScreen({ apiKey, onApiKeyChange, model, onModelChange, usage, onSubmit, error, lockedUsername = '' }: {
  apiKey: string
  onApiKeyChange: (k: string) => void
  model: string
  onModelChange: (m: string) => void
  usage: UsageState
  onSubmit: (username: string) => void
  error: string | null
  lockedUsername?: string
}) {
  const [username, setUsername] = useState('')
  const [showKey, setShowKey] = useState(false)

  useEffect(() => { if (lockedUsername) setUsername(lockedUsername) }, [lockedUsername])

  const activeUsername = lockedUsername || username
  const canSubmit = activeUsername.trim().length > 0 && apiKey.trim().length > 0

  function modelOptionLabel(m: string) {
    const limit = FREE_TIER[m]?.rpd ?? 1500
    const used  = usage.counts[m] ?? 0
    if (usage.exceeded[m]) return `${MODEL_LABELS[m]}  —  quota exceeded today`
    if (used > 0) return `${MODEL_LABELS[m]}  ·  ${(limit - used).toLocaleString()} of ${limit.toLocaleString()} left`
    return `${MODEL_LABELS[m]}  ·  ${limit.toLocaleString()}/day free`
  }

  function usageHint() {
    const limit = FREE_TIER[model]?.rpd ?? 1500
    const used  = usage.counts[model] ?? 0
    if (usage.exceeded[model]) return { text: 'quota exceeded for today — resets at midnight UTC', warn: true }
    if (used > 0) return { text: `${used} request${used > 1 ? 's' : ''} used today · ${(limit - used).toLocaleString()} of ${limit.toLocaleString()} remaining`, warn: false }
    return { text: `${limit.toLocaleString()} requests/day on the free tier`, warn: false }
  }

  const hint = usageHint()

  return (
    <div className="screen">
      <div className="hero">
        <div className="eyebrow">
          <span className="eyebrow-dot" />
          a curated suggestion engine
        </div>
        <h1 className="display">
          Find your next <em>quiet obsession</em>.
        </h1>
        <p className="lede">
          Drop in your AniList username and a Gemini key — we'll read your ratings
          like tea leaves and hand back five anime series, five films, and five games
          worth your weekend.
        </p>
      </div>

      <form className="card form"
        onSubmit={(e) => { e.preventDefault(); if (canSubmit) onSubmit(activeUsername.trim()) }}>
        <div className="field">
          <label htmlFor="u">
            <span className="label-num">01</span>
            AniList username
            <span className="label-hint">{lockedUsername ? '● connected' : 'public profile'}</span>
          </label>
          <div className="input-wrap">
            <span className="input-prefix">anilist.co/user/</span>
            <input id="u" type="text" placeholder="hoshikawa"
              value={activeUsername}
              onChange={(e) => { if (!lockedUsername) setUsername(e.target.value) }}
              disabled={!!lockedUsername}
              autoComplete="off" spellCheck={false} />
          </div>
        </div>

        <div className="field">
          <label htmlFor="k">
            <span className="label-num">02</span>
            Gemini API key
            <span className="label-hint">stored locally, never sent elsewhere</span>
          </label>
          <div className="input-wrap">
            <input id="k" type={showKey ? 'text' : 'password'} placeholder="AIza••••••••••••••••••••••"
              value={apiKey} onChange={(e) => onApiKeyChange(e.target.value)}
              autoComplete="off" spellCheck={false} />
            <button type="button" className="show-toggle"
              onClick={() => setShowKey(s => !s)}
              aria-label={showKey ? 'Hide key' : 'Show key'}>
              {showKey ? 'hide' : 'show'}
            </button>
          </div>
        </div>

        <div className="field">
          <label htmlFor="m">
            <span className="label-num">03</span>
            Gemini model
            <span className="label-hint">free tier</span>
          </label>
          <div className="input-wrap">
            <select id="m" value={model} onChange={e => onModelChange(e.target.value)}>
              {MODELS.map(m => (
                <option key={m} value={m}>{modelOptionLabel(m)}</option>
              ))}
            </select>
          </div>
          <p className={`usage-hint${hint.warn ? ' usage-hint--warn' : ''}`}>{hint.text}</p>
        </div>

        {error && <div className="inline-error">{error}</div>}

        <button type="submit" className="cta" disabled={!canSubmit}>
          <span>Read my list</span>
          <span className="cta-arrow">→</span>
        </button>

        <p className="fineprint">
          We touch the AniList GraphQL API once and pass anonymised highlights to Gemini.
          No account, no tracking, no saved keys.
        </p>
      </form>
    </div>
  )
}

// ─── Loading screen ───────────────────────────────────────────────────────────

const LOADING_LINES = [
  'connecting to anilist…',
  'loading your watch history…',
  'reading your ratings and taste profile…',
  'weighing your genre preferences…',
  'consulting gemini for recommendations…',
  'curating five series, five films, five games…',
  'adding the finishing touches…',
]

function LoadingScreen() {
  const [lineIdx, setLineIdx] = useState(0)
  const [typed, setTyped] = useState('')

  useEffect(() => {
    const line = LOADING_LINES[lineIdx]
    if (typed.length < line.length) {
      const t = setTimeout(() => setTyped(line.slice(0, typed.length + 1)), 22)
      return () => clearTimeout(t)
    }
    const next = setTimeout(() => {
      setLineIdx(i => (i + 1) % LOADING_LINES.length)
      setTyped('')
    }, 800)
    return () => clearTimeout(next)
  }, [typed, lineIdx])

  return (
    <div className="screen loading">
      <div className="loading-card">
        <div className="loading-orbit" aria-hidden="true">
          <div className="orbit-dot" />
          <div className="orbit-ring" />
          <div className="orbit-ring r2" />
          <div className="orbit-ring r3" />
        </div>
        <div className="loading-log">
          {LOADING_LINES.slice(0, lineIdx).map((l, i) => (
            <div key={i} className="log-line done">
              <span className="log-mark">✓</span>{l}
            </div>
          ))}
          <div className="log-line active">
            <span className="log-mark spinning">◐</span>
            {typed}<span className="caret">▍</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Cover image hook ─────────────────────────────────────────────────────────
// Anime → AniList GraphQL (browser-direct)
// Games → backend /game-cover (proxies RAWG, keeps key server-side)

const BACKEND = (import.meta.env.VITE_BACKEND_URL as string | undefined) ?? ''

interface CoverImageResult { url: string | null; mediaId: number | null }

function useCoverImage(title: string, category: 'series' | 'movies' | 'games'): CoverImageResult {
  const [url, setUrl] = useState<string | null>(null)
  const [mediaId, setMediaId] = useState<number | null>(null)

  useEffect(() => {
    if (!title) return
    let cancelled = false

    if (category === 'games') {
      fetch(`${BACKEND}/game-cover?title=${encodeURIComponent(title)}`)
        .then(r => r.json())
        .then((data: { url: string | null }) => {
          if (!cancelled && data.url) setUrl(data.url)
        })
        .catch(() => {})
    } else {
      fetch('https://graphql.anilist.co', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `query($s:String){Media(search:$s,type:ANIME,isAdult:false){id coverImage{large}}}`,
          variables: { s: title },
        }),
      })
        .then(r => r.json())
        .then(data => {
          if (!cancelled) {
            const media = data?.data?.Media
            if (media?.coverImage?.large) setUrl(media.coverImage.large)
            if (media?.id) setMediaId(media.id)
          }
        })
        .catch(() => {})
    }

    return () => { cancelled = true }
  }, [title, category])

  return { url, mediaId }
}

// ─── Game card (simple flat info card, no poster) ────────────────────────────

function GameCard({ item, hue, idx }: { item: Recommendation; hue: number; idx: number }) {
  return (
    <article
      className="game-card"
      style={{ animationDelay: `${idx * 60}ms` } as React.CSSProperties}
    >
      <div className="game-card-top">
        <div className="game-card-match">
          <span className="match-num">{item.match_score}</span>
          <span className="match-pct">% match</span>
        </div>
        {(item.year || item.studio) && (
          <div className="result-meta">
            {item.year && <span>{item.year}</span>}
            {item.year && item.studio && <span style={{ opacity: 0.5 }}>·</span>}
            {item.studio && <span>{item.studio}</span>}
          </div>
        )}
      </div>
      <h3 className="game-card-title" style={{ color: `oklch(0.78 0.08 ${hue})` }}>
        {item.title}
      </h3>
      <p className="result-why">{item.reason}</p>
      {item.genres.length > 0 && (
        <div className="result-tags">
          {item.genres.map(g => <span key={g} className="tag">{g}</span>)}
        </div>
      )}
      {item.similar && (
        <div className="result-similar">
          <span className="similar-label">because you liked</span>
          <span className="similar-name">{item.similar}</span>
        </div>
      )}
    </article>
  )
}

// ─── AniList save helpers ─────────────────────────────────────────────────────

type AniListStatus = 'PLANNING' | 'COMPLETED' | 'DROPPED'
type SelectionEntry = { mediaId: number; title: string; status: AniListStatus }

const STATUS_LABELS: Record<AniListStatus, string> = {
  PLANNING:  'Plan to Watch',
  COMPLETED: 'Completed',
  DROPPED:   "Won't Watch",
}

async function batchSaveToAniList(entries: SelectionEntry[], token: string): Promise<void> {
  const query = entries
    .map((e, i) => `e${i}: SaveMediaListEntry(mediaId:${e.mediaId},status:${e.status}){id status}`)
    .join('\n')
  const res = await fetch('https://graphql.anilist.co', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ query: `mutation{${query}}` }),
  })
  const data = await res.json() as { errors?: Array<{ message: string }> }
  if (data.errors?.length) throw new Error(data.errors[0].message)
  if (!res.ok) throw new Error(`AniList HTTP ${res.status}`)
}

// ─── Anime card (flip: front = poster, back = details) ────────────────────────

const STATUS_OPTIONS: { status: AniListStatus; label: string }[] = [
  { status: 'PLANNING',  label: 'Plan to Watch' },
  { status: 'COMPLETED', label: 'Completed'     },
  { status: 'DROPPED',   label: "Won't Watch"   },
]

function AnimeCard({ item, hue, idx, category, anilistToken, selectedStatus, onSelect }: {
  item: Recommendation
  hue: number
  idx: number
  category: 'series' | 'movies'
  anilistToken: string
  selectedStatus: AniListStatus | null
  onSelect: (mediaId: number, title: string, status: AniListStatus | null) => void
}) {
  const [flipped, setFlipped] = useState(false)
  const [actionMode, setActionMode] = useState(false)
  const { url: coverUrl, mediaId } = useCoverImage(item.title, category)

  function handleClick(e: React.MouseEvent) {
    if (actionMode) return
    if (flipped) {
      if (anilistToken && mediaId) { e.stopPropagation(); setActionMode(true) }
    } else {
      setFlipped(true)
    }
  }

  function handleMouseLeave() {
    setActionMode(false)
    setFlipped(false)
  }

  function selectStatus(status: AniListStatus, e: React.MouseEvent) {
    e.stopPropagation()
    if (!mediaId) return
    onSelect(mediaId, item.title, selectedStatus === status ? null : status)
    setActionMode(false)
  }

  return (
    <div
      className={`card-flip${flipped || actionMode ? ' is-flipped' : ''}`}
      style={{ animationDelay: `${idx * 60}ms` } as React.CSSProperties}
      onMouseEnter={() => setFlipped(true)}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label={item.title}
      onKeyDown={e => { if (e.key === 'Enter') handleClick(e as unknown as React.MouseEvent) }}
    >
      <div className="card-inner">
        <div className="card-front">
          {coverUrl
            ? <img className="card-cover" src={coverUrl} alt={item.title} />
            : <CoverPlaceholder label={`COVER ${String(idx + 1).padStart(2, '0')}`} hue={hue} h={340} />
          }
          <div className="card-name-overlay">
            <h3 className="card-name">{item.title}</h3>
            {(item.year || item.studio) && (
              <p className="card-name-meta">
                {[item.year, item.studio].filter(Boolean).join(' · ')}
              </p>
            )}
          </div>
          {selectedStatus && (
            <div className="card-front-badge" title={STATUS_LABELS[selectedStatus]}>
              {selectedStatus === 'COMPLETED' ? '✓' : selectedStatus === 'PLANNING' ? '⋯' : '✕'}
            </div>
          )}
        </div>

        <div className="card-back">
          {actionMode ? (
            <div className="card-action-panel">
              <button className="card-action-close"
                onClick={e => { e.stopPropagation(); setActionMode(false) }}>✕</button>
              <p className="card-action-title">{item.title}</p>
              <div className="card-action-btns">
                {STATUS_OPTIONS.map(({ status, label }) => (
                  <button
                    key={status}
                    className={`card-action-btn${selectedStatus === status ? ' card-action-btn--active' : ''}`}
                    onClick={e => selectStatus(status, e)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="card-back-match">
                <span className="match-num">{item.match_score}</span>
                <span className="match-pct">% match</span>
              </div>
              <h3 className="card-back-title">{item.title}</h3>
              {(item.year || item.studio) && (
                <div className="result-meta">
                  {item.year && <span>{item.year}</span>}
                  {item.year && item.studio && <span style={{ opacity: 0.5 }}>·</span>}
                  {item.studio && <span>{item.studio}</span>}
                </div>
              )}
              <p className="result-why">{item.reason}</p>
              {item.genres.length > 0 && (
                <div className="result-tags">
                  {item.genres.map(g => <span key={g} className="tag">{g}</span>)}
                </div>
              )}
              <div className="card-back-bottom">
                {item.similar && (
                  <div className="result-similar">
                    <span className="similar-label">because you liked</span>
                    <span className="similar-name">{item.similar}</span>
                  </div>
                )}
                <p className="card-back-connect-hint">
                  {!anilistToken
                    ? 'connect AniList to save'
                    : !mediaId
                    ? 'loading…'
                    : selectedStatus
                    ? `✓ ${STATUS_LABELS[selectedStatus]} — click to change`
                    : 'click to add to AniList'}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Help / get-started modal ────────────────────────────────────────────────

function HelpModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal help-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Get started</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="help-body">

          <div className="help-section">
            <div className="help-section-eyebrow">step 01</div>
            <h3 className="help-section-title">Get a free Gemini API key</h3>
            <ol className="help-steps">
              <li>Go to <strong>aistudio.google.com</strong></li>
              <li>Sign in with your Google account</li>
              <li>Click <strong>Get API key</strong> in the left sidebar</li>
              <li>Click <strong>Create API key</strong> and select any project</li>
              <li>Copy the key and paste it into the <em>Gemini API key</em> field on the home screen</li>
            </ol>
            <p className="help-note">Free tier: 1,500 requests/day — plenty for personal use.</p>
          </div>

          <div className="help-divider" />

          <div className="help-section">
            <div className="help-section-eyebrow">step 02</div>
            <h3 className="help-section-title">Save suggestions to your AniList</h3>
            <ol className="help-steps">
              <li>Click <strong>Connect AL</strong> in the top-right corner</li>
              <li>Authorise the app on AniList — you'll be redirected back automatically</li>
              <li>Enter your username and click <em>Read my list</em> to get recommendations</li>
              <li>Hover a card to flip it, then <strong>click the flipped card</strong> to open the status picker</li>
              <li>Choose <em>Plan to Watch</em>, <em>Completed</em>, or <em>Won't Watch</em> for each anime</li>
              <li>A floating <strong>Save to AniList</strong> bar appears once you have selections</li>
              <li>Click it, review the list, and hit <strong>Confirm</strong> — all saved in one request</li>
            </ol>
          </div>

        </div>
      </div>
    </div>
  )
}

// ─── Save modal ───────────────────────────────────────────────────────────────

function SaveModal({ selections, token, onClose }: {
  selections: SelectionEntry[]
  token: string
  onClose: () => void
}) {
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleConfirm() {
    setSaving(true)
    setError(null)
    try {
      await batchSaveToAniList(selections, token)
      setSaved(true)
      setTimeout(onClose, 1600)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed. Try again.')
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Save to AniList</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          {selections.map(s => (
            <div key={s.title} className="modal-entry">
              <span className="modal-entry-title">{s.title}</span>
              <span className={`modal-entry-badge modal-entry-badge--${s.status.toLowerCase()}`}>
                {STATUS_LABELS[s.status]}
              </span>
            </div>
          ))}
        </div>
        {error && <p className="modal-error">{error}</p>}
        <div className="modal-footer">
          {saved ? (
            <p className="modal-saved-msg">✓ All saved to AniList</p>
          ) : (
            <button className="cta" style={{ width: '100%' }} onClick={handleConfirm} disabled={saving}>
              <span>{saving ? 'Saving…' : `Confirm · ${selections.length} entr${selections.length === 1 ? 'y' : 'ies'}`}</span>
              {!saving && <span className="cta-arrow">→</span>}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Results screen ───────────────────────────────────────────────────────────

const CATS = [
  { key: 'series' as const, title: 'anime series', hue: 280 },
  { key: 'movies' as const, title: 'anime films',  hue: 20  },
  { key: 'games'  as const, title: 'games',         hue: 160 },
]

function ResultsScreen({ result, onReset, anilistToken }: {
  result: RecommendationResponse
  onReset: () => void
  anilistToken: string
}) {
  const { profile } = result
  const [selections, setSelections] = useState<Record<string, SelectionEntry>>({})
  const [showModal, setShowModal] = useState(false)

  function handleSelect(mediaId: number, title: string, status: AniListStatus | null) {
    setSelections(prev => {
      const next = { ...prev }
      if (status === null) delete next[title]
      else next[title] = { mediaId, title, status }
      return next
    })
  }

  const selectionList = Object.values(selections)

  return (
    <div className="screen results">
      <header className="results-header">
        <button className="back" onClick={onReset}>
          <span className="back-arrow">←</span> start over
        </button>
        <div className="profile-pill">
          <div className="avatar-blob" />
          <div>
            <div className="profile-name">{profile.username}</div>
            <div className="profile-stats">
              {profile.watched} watched{profile.mean_score > 0 ? ` · ⌀ ${profile.mean_score}` : ''}
            </div>
          </div>
        </div>
      </header>

      <section className="summary">
        <div className="summary-eyebrow">we noticed</div>
        <h2 className="summary-headline">
          {profile.top_genres[0]
            ? <>You lean toward <em>{profile.top_genres[0].toLowerCase()}</em>{profile.top_genres[1] ? <> and <em>{profile.top_genres[1].toLowerCase()}</em></> : null}, </>
            : null}
          {profile.mean_score > 0
            ? <>rate shows with an average of <em>{profile.mean_score}/10</em>, </>
            : null}
          {profile.recent_fav
            ? <>and your top pick is <em>{profile.recent_fav}</em>.</>
            : <>and you have great taste.</>}
        </h2>
        <p className="summary-sub">
          Fifteen suggestions below, weighted toward what you actually finish — not just what's popular.
        </p>
      </section>

      {CATS.map(cat => {
        const items = result[cat.key]
        if (!items.length) return null
        return (
          <section key={cat.key} className="category">
            <div className="cat-head">
              <div className="cat-marker"
                style={{ background: `oklch(0.85 0.08 ${cat.hue})` }} />
              <h2 className="cat-title">{cat.title}</h2>
              <span className="cat-count">{items.length} picks</span>
            </div>
            <div className={cat.key === 'games' ? 'games-grid' : 'cat-grid'}>
              {items.map((item, i) =>
                cat.key === 'games'
                  ? <GameCard key={item.title} item={item} hue={cat.hue} idx={i} />
                  : <AnimeCard
                      key={item.title} item={item} hue={cat.hue} idx={i}
                      category={cat.key} anilistToken={anilistToken}
                      selectedStatus={selections[item.title]?.status ?? null}
                      onSelect={handleSelect}
                    />
              )}
            </div>
          </section>
        )
      })}

      <footer className="results-footer">
        <div className="footer-line" />
        <p>
          that&apos;s the lot. refresh for another pass, or{' '}
          <button className="link-btn" onClick={onReset}>try a different list</button>.
        </p>
      </footer>

      {anilistToken && selectionList.length > 0 && (
        <div className="save-bar">
          <span className="save-bar-count">{selectionList.length} selected</span>
          <button className="cta save-bar-btn" onClick={() => setShowModal(true)}>
            <span>Save to AniList</span>
            <span className="cta-arrow">→</span>
          </button>
        </div>
      )}

      {showModal && (
        <SaveModal
          selections={selectionList}
          token={anilistToken}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

// ─── Root app ─────────────────────────────────────────────────────────────────

export default function App() {
  const [theme, setTheme] = useLocalStorage<Theme>('animeSenseiTheme', 'dark')
  const [stage, setStage] = useState<Stage>('input')
  const [apiKey, setApiKey] = useLocalStorage<string>('animeSenseiGeminiKey', '')
  const [model, setModel] = useLocalStorage<string>('animeSenseiModel', 'gemini-2.5-flash-lite')
  const [rawUsage, setRawUsage] = useLocalStorage<UsageState>('animeSenseiUsage', freshUsage())
  const [anilistToken, setAnilistToken] = useLocalStorage<string>('animeSenseiAniListToken', '')
  const [anilistUsername, setAnilistUsername] = useState('')
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [seenHelp, setSeenHelp] = useLocalStorage<boolean>('animeSenseiSeenHelp', false)
  const [showHelp, setShowHelp] = useState(!seenHelp)

  // Auto-reset usage when the UTC date rolls over
  const usage = rawUsage.date === todayUTC() ? rawUsage : freshUsage()

  function recordUsage(m: string, quotaExceeded: boolean) {
    const next: UsageState = {
      date: todayUTC(),
      counts:   { ...usage.counts,   [m]: (usage.counts[m]   ?? 0) + 1 },
      exceeded: { ...usage.exceeded, ...(quotaExceeded ? { [m]: true } : {}) },
    }
    setRawUsage(next)
  }

  useEffect(() => {
    const BG: Record<string, string> = {
      dark:  'oklch(0.18 0.025 280)',
      light: 'oklch(0.985 0.008 70)',
    }
    document.documentElement.dataset.theme = theme
    document.documentElement.style.background = BG[theme] ?? BG.dark
  }, [theme])

  useEffect(() => {
    if (!anilistToken) { setAnilistUsername(''); return }
    fetch('https://graphql.anilist.co', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${anilistToken}` },
      body: JSON.stringify({ query: '{ Viewer { name } }' }),
    })
      .then(r => r.json())
      .then(data => { const n = data?.data?.Viewer?.name; if (n) setAnilistUsername(n) })
      .catch(() => {})
  }, [anilistToken])


  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1))
    const token = params.get('access_token')
    if (token) {
      setAnilistToken(token)
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }, [])

  function connectAniList() {
    window.location.href = '/auth/anilist'
  }

  async function handleSubmit(username: string) {
    setError(null)
    setStage('loading')
    try {
      const data = await getRecommendations(username, model, apiKey)
      recordUsage(model, false)
      setResult(data)
      setStage('results')
    } catch (e: unknown) {
      const err = e as ApiError
      const isQuota   = err.status === 429
      const isGemini  = err.status === 502 || (err.detail ?? '').toLowerCase().includes('gemini')
      if (isQuota || isGemini) recordUsage(model, isQuota)
      setError(err.detail ?? 'Something went wrong. Please try again.')
      setStage('input')
    }
  }

  return (
    <>
      <Backdrop />
      <div className="topbar">
        <div className="logo">
          <div className="logo-mark" />
          <span className="logo-text">sensei</span>
          <span className="logo-sub">· anime suggestions, refined</span>
        </div>
        <div className="topbar-right">
          <button
            className="theme-toggle"
            onClick={() => setShowHelp(true)}
            aria-label="Get started guide"
            title="Get started">
            ?
          </button>
          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            aria-label="Toggle theme">
            {theme === 'light' ? '☾' : '☀'}
          </button>
          {anilistToken ? (
            <button
              className="topbar-anilist-btn topbar-anilist-btn--connected"
              onClick={() => setAnilistToken('')}
              title="Disconnect AniList"
            >
              AL ✓
            </button>
          ) : (
            <button
              className="topbar-anilist-btn"
              onClick={connectAniList}
              title="Connect AniList to save anime"
            >
              Connect AL
            </button>
          )}
        </div>
      </div>

      {showHelp && <HelpModal onClose={() => { setShowHelp(false); setSeenHelp(true) }} />}

      <main className="app">
        {stage === 'input' && (
          <InputScreen
            apiKey={apiKey}
            onApiKeyChange={setApiKey}
            model={model}
            onModelChange={setModel}
            usage={usage}
            onSubmit={handleSubmit}
            error={error}
            lockedUsername={anilistUsername}
          />
        )}
        {stage === 'loading' && <LoadingScreen />}
        {stage === 'results' && result && (
          <ResultsScreen result={result} onReset={() => setStage('input')} anilistToken={anilistToken} />
        )}
      </main>
    </>
  )
}
