interface Props {
  notes: string
}

export function NotesCard({ notes }: Props) {
  return (
    <div style={{
      background: '#fffdf7',
      border: '1px solid #fde68a',
      borderLeft: '4px solid var(--gold)',
      borderRadius: 'var(--radius-md)',
      padding: '1rem 1.2rem',
      marginBottom: '1.5rem',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        marginBottom: '0.5rem',
      }}>
        <span style={{ fontSize: '1rem' }}>📋</span>
        <span style={{
          fontSize: '0.7rem',
          fontWeight: 700,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'var(--gold)',
        }}>
          Profile Considerations
        </span>
      </div>
      <p style={{
        fontSize: '0.875rem',
        color: '#78350f',
        lineHeight: 1.7,
        margin: 0,
      }}>
        {notes}
      </p>
    </div>
  )
}
