import { fmtDuration, secondsUntilMidnightUTC } from '../constants'

interface Props {
  type: 'quota' | 'auth' | 'error' | 'anilist' | 'gemini'
  message: string
}

const CONFIG = {
  quota:   { bg: 'var(--warning-bg)',  border: 'var(--warning-border)', color: 'var(--warning)',  icon: '⏱',  title: 'Quota reached'        },
  auth:    { bg: 'var(--error-bg)',    border: 'var(--error-border)',   color: 'var(--error)',    icon: '🔑',  title: 'API key error'        },
  anilist: { bg: 'var(--warning-bg)',  border: 'var(--warning-border)', color: 'var(--warning)',  icon: '📡',  title: 'AniList unreachable'  },
  gemini:  { bg: 'var(--error-bg)',    border: 'var(--error-border)',   color: 'var(--error)',    icon: '🤖',  title: 'Gemini unavailable'   },
  error:   { bg: 'var(--error-bg)',    border: 'var(--error-border)',   color: 'var(--error)',    icon: '🚫',  title: 'Error'                },
}

export function ErrorBanner({ type, message }: Props) {
  const { bg, border, color, icon, title } = CONFIG[type]

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 'var(--radius-md)',
      padding: '1rem 1.2rem',
      margin: '1rem 0',
    }}>
      <div style={{ fontSize: '0.92rem', fontWeight: 600, color, marginBottom: '4px' }}>
        {icon} {title}
      </div>
      <div style={{ fontSize: '0.84rem', color: 'var(--muted)', lineHeight: 1.6 }}>
        {message}
        {type === 'quota' && (
          <> Resets in <strong style={{ color }}>{fmtDuration(secondsUntilMidnightUTC())}</strong> (midnight UTC).</>
        )}
      </div>
    </div>
  )
}
