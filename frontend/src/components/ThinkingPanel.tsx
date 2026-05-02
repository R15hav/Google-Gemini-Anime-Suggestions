import { useState } from 'react'

interface Props {
  thinking: string
}

export function ThinkingPanel({ thinking }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      marginBottom: '1.5rem',
      background: 'var(--surface)',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.75rem 1.1rem',
          background: 'var(--surface-2)',
          cursor: 'pointer',
          border: 'none',
          borderBottom: open ? '1px solid var(--border)' : 'none',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#ede9e0' }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-2)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.95rem' }}>🧠</span>
          <span style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
          }}>
            Gemini&apos;s Thinking Process
          </span>
        </div>
        <span style={{
          fontSize: '0.75rem',
          color: 'var(--muted-2)',
          transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
          display: 'inline-block',
        }}>
          ▼
        </span>
      </button>

      {open && (
        <div style={{ padding: '1rem 1.1rem' }}>
          <p style={{
            fontSize: '0.845rem',
            color: 'var(--muted)',
            lineHeight: 1.75,
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}>
            {thinking}
          </p>
        </div>
      )}
    </div>
  )
}
