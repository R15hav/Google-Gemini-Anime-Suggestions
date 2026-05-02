import { useEffect, useRef, useState } from 'react'
import { validateUser } from '../api'
import { FREE_TIER, MODELS, nextFallbackModel } from '../constants'
import type { ValidationResult } from '../types'

interface Props {
  apiKey: string
  username: string
  model: string
  quotaHitModel: string | null
  onApiKeyChange: (k: string) => void
  onUsernameChange: (u: string) => void
  onModelChange: (m: string) => void
  onValidationResult: (r: ValidationResult | null) => void
  validationResult: ValidationResult | null
  onClose: () => void
}

export function SettingsModal({
  apiKey, username, model, quotaHitModel,
  onApiKeyChange, onUsernameChange, onModelChange,
  onValidationResult, validationResult, onClose,
}: Props) {
  const [localUser, setLocalUser] = useState(username)
  const [validating, setValidating] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setLocalUser(username)
  }, [username])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  function handleUsernameChange(val: string) {
    setLocalUser(val)
    onUsernameChange(val)
    onValidationResult(null)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!val.trim()) return
    debounceRef.current = setTimeout(async () => {
      setValidating(true)
      try {
        const r = await validateUser(val.trim())
        onValidationResult({ status: 'ok', message: `${r.completed_count} completed anime found.` })
      } catch (e: unknown) {
        const httpStatus = (e as { status?: number }).status
        const detail = (e as { detail?: string }).detail ?? ''
        const lower = detail.toLowerCase()
        if (!httpStatus) {
          onValidationResult({ status: 'backend', message: 'Cannot reach the backend. Make sure the server is running.' })
        } else if (lower.includes('anilist') && httpStatus === 502) {
          onValidationResult({ status: 'anilist', message: detail })
        } else if (httpStatus === 404 && (!detail || detail === 'Not Found')) {
          onValidationResult({ status: 'backend', message: 'Backend returned an unexpected response. Try restarting the server.' })
        } else {
          onValidationResult({ status: 'error', message: detail || 'Unknown error.' })
        }
      } finally {
        setValidating(false)
      }
    }, 600)
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.6rem 0.85rem',
    borderRadius: 'var(--radius-sm)',
    border: '1px solid var(--border)',
    background: 'var(--surface-2)',
    color: 'var(--ink)',
    fontSize: '0.92rem',
    outline: 'none',
    transition: 'border-color 0.15s, box-shadow 0.15s',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: '0.7rem',
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: 'var(--muted)',
    marginBottom: '6px',
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(26,26,26,0.45)',
        backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 1000,
        animation: 'fadeIn 0.18s ease',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
          padding: '1.75rem',
          width: '100%',
          maxWidth: '420px',
          margin: '0 1rem',
          animation: 'fadeUp 0.22s ease',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--ink)' }}>
            Settings
          </h2>
          <button
            onClick={onClose}
            style={{ fontSize: '1.1rem', color: 'var(--muted)', padding: '2px 6px', borderRadius: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* API Key */}
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={labelStyle}>🔑 Gemini API Key</label>
          <input
            type="password"
            value={apiKey}
            placeholder="AIza…"
            style={inputStyle}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(220,38,38,0.1)' }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
            onChange={e => onApiKeyChange(e.target.value)}
          />
          {apiKey ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
              <span style={{ fontSize: '0.82rem', color: 'var(--success)' }}>✓ Saved to this browser</span>
              <button
                onClick={() => onApiKeyChange('')}
                style={{ fontSize: '0.78rem', color: 'var(--muted)', textDecoration: 'underline', cursor: 'pointer' }}
              >
                Clear
              </button>
            </div>
          ) : (
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '6px' }}>
              Get a free key at{' '}
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                aistudio.google.com →
              </a>
            </p>
          )}
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1rem 0' }} />

        {/* Username */}
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={labelStyle}>🎌 AniList Username</label>
          <input
            type="text"
            value={localUser}
            placeholder="your_username"
            style={inputStyle}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(220,38,38,0.1)' }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
            onChange={e => handleUsernameChange(e.target.value)}
          />
          {validating && (
            <p style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: '6px' }}>Checking profile…</p>
          )}
          {!validating && validationResult && (
            <ValidationChip result={validationResult} />
          )}
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1rem 0' }} />

        {/* Model */}
        <div style={{ marginBottom: '0.5rem' }}>
          <label style={labelStyle}>🤖 Gemini Model</label>
          <select
            value={model}
            onChange={e => onModelChange(e.target.value)}
            style={{ ...inputStyle, appearance: 'none', backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'8\' viewBox=\'0 0 12 8\'%3E%3Cpath d=\'M1 1l5 5 5-5\' stroke=\'%236b7280\' stroke-width=\'1.5\' fill=\'none\'/%3E%3C/svg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.75rem center', paddingRight: '2rem' }}
          >
            {MODELS.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>

          {quotaHitModel === model && (
            <p style={{ fontSize: '0.8rem', color: 'var(--warning)', marginTop: '6px' }}>
              ⚠ Quota hit on this model. Try <strong>{nextFallbackModel(model)}</strong>.
            </p>
          )}

          {FREE_TIER[model] && (
            <p style={{ fontSize: '0.76rem', color: 'var(--muted-2)', marginTop: '6px' }}>
              Free tier: {FREE_TIER[model].rpd} req/day · {FREE_TIER[model].rpm} rpm · resets midnight UTC
            </p>
          )}
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1.25rem 0 0.75rem' }} />
        <p style={{ fontSize: '0.76rem', color: 'var(--muted-2)' }}>ℹ Your AniList list must be <strong>public</strong>.</p>
      </div>
    </div>
  )
}

const CHIP_CONFIG: Record<string, { bg: string; border: string; color: string; icon: string }> = {
  ok:      { bg: 'var(--success-bg,  #f0fdf4)', border: 'var(--success-border, #bbf7d0)', color: 'var(--success)',  icon: '✓' },
  warn:    { bg: 'var(--warning-bg)',            border: 'var(--warning-border)',           color: 'var(--warning)', icon: '⚠' },
  anilist: { bg: 'var(--warning-bg)',            border: 'var(--warning-border)',           color: 'var(--warning)', icon: '📡' },
  backend: { bg: 'var(--error-bg)',              border: 'var(--error-border)',             color: 'var(--error)',   icon: '🔌' },
  error:   { bg: 'var(--error-bg)',              border: 'var(--error-border)',             color: 'var(--error)',   icon: '✕' },
}

function ValidationChip({ result }: { result: { status: string; message: string } }) {
  const { bg, border, color, icon } = CHIP_CONFIG[result.status] ?? CHIP_CONFIG.error
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '8px',
      background: bg, border: `1px solid ${border}`,
      borderRadius: 'var(--radius-sm)',
      padding: '0.5rem 0.75rem', marginTop: '8px',
    }}>
      <span style={{ fontSize: '0.85rem', color, flexShrink: 0, lineHeight: 1.5 }}>{icon}</span>
      <span style={{ fontSize: '0.82rem', color, lineHeight: 1.5 }}>{result.message}</span>
    </div>
  )
}
