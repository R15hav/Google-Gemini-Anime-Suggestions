import { fmtDuration, secondsUntilMidnightUTC } from '../constants'

interface Props {
  type: 'quota' | 'auth' | 'error'
  message: string
}

export function ErrorBanner({ type, message }: Props) {
  const isQuota = type === 'quota'

  const bg = isQuota ? 'var(--warning-bg)' : 'var(--error-bg)'
  const border = isQuota ? 'var(--warning-border)' : 'var(--error-border)'
  const titleColor = isQuota ? 'var(--warning)' : 'var(--error)'
  const icon = isQuota ? '⏱' : '🚫'
  const title = isQuota ? 'Quota reached' : 'Error'

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 'var(--radius-md)',
      padding: '1rem 1.2rem',
      margin: '1rem 0',
    }}>
      <div style={{ fontSize: '0.92rem', fontWeight: 600, color: titleColor, marginBottom: '4px' }}>
        {icon} {title}
      </div>
      <div style={{ fontSize: '0.84rem', color: 'var(--muted)', lineHeight: 1.6 }}>
        {message}
        {isQuota && (
          <> Resets in <strong style={{ color: titleColor }}>{fmtDuration(secondsUntilMidnightUTC())}</strong> (midnight UTC).</>
        )}
      </div>
    </div>
  )
}
