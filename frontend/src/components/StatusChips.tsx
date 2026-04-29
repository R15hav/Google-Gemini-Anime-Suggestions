interface Props {
  hasKey: boolean
  username: string
  profileOk: boolean
  model: string
  onOpenSettings: () => void
}

export function StatusChips({ hasKey, username, profileOk, model, onOpenSettings }: Props) {
  const dot = (color: string) => (
    <span style={{
      display: 'inline-block',
      width: '7px',
      height: '7px',
      borderRadius: '50%',
      background: color,
      marginRight: '5px',
      verticalAlign: 'middle',
    }} />
  )

  const chip = (content: React.ReactNode) => (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '4px 12px',
      borderRadius: '99px',
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      fontSize: '0.78rem',
      fontWeight: 500,
      color: 'var(--ink)',
      boxShadow: 'var(--shadow-sm)',
    }}>
      {content}
    </span>
  )

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px',
      justifyContent: 'center',
      marginBottom: '1.75rem',
    }}>
      {chip(<>{dot(hasKey ? '#16a34a' : '#dc2626')}{hasKey ? 'Key ready' : 'No key'}</>)}
      {chip(<>
        {dot(profileOk ? '#16a34a' : username ? '#dc2626' : '#d97706')}
        {profileOk ? username : username ? 'Invalid profile' : 'No profile'}
      </>)}
      {chip(<>{dot('#b45309')}{model}</>)}
      <button
        onClick={onOpenSettings}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 12px',
          borderRadius: '99px',
          background: 'transparent',
          border: '1px dashed var(--border-2)',
          fontSize: '0.75rem',
          color: 'var(--muted)',
          cursor: 'pointer',
          transition: 'border-color 0.15s, color 0.15s',
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)'
          ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)'
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-2)'
          ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--muted)'
        }}
      >
        ✦ configure ⚙
      </button>
    </div>
  )
}
