export function Hero() {
  return (
    <header style={{ textAlign: 'center', padding: '2.5rem 0 2rem' }}>
      <div style={{ fontSize: '3rem', marginBottom: '0.75rem', filter: 'drop-shadow(0 2px 8px rgba(180,83,9,0.25))' }}>
        🏯
      </div>
      <h1 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: 'clamp(2rem, 5vw, 2.8rem)',
        fontWeight: 800,
        color: 'var(--ink)',
        letterSpacing: '-0.02em',
        lineHeight: 1.15,
        marginBottom: '0.5rem',
      }}>
        Anime Sensei
      </h1>
      <div style={{
        width: '48px',
        height: '3px',
        background: 'var(--accent)',
        margin: '0 auto 0.9rem',
        borderRadius: '2px',
      }} />
      <p style={{
        color: 'var(--muted)',
        fontSize: '0.97rem',
        maxWidth: '340px',
        margin: '0 auto',
        lineHeight: 1.6,
      }}>
        Discover your next obsession, powered by AI&nbsp;&amp;&nbsp;your AniList history
      </p>
    </header>
  )
}
