import type { Recommendation } from '../types'

interface Props {
  rec: Recommendation
  index: number
}

export function RecommendationCard({ rec, index }: Props) {
  const score = rec.match_score

  let scoreColor = '#dc2626'
  let scoreBg = '#fef2f2'
  if (score >= 85) { scoreColor = '#16a34a'; scoreBg = '#f0fdf4' }
  else if (score >= 70) { scoreColor = '#d97706'; scoreBg = '#fffbeb' }

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      boxShadow: 'var(--shadow-sm)',
      marginBottom: '0.85rem',
      animation: `fadeUp 0.4s ease ${index * 0.07}s both`,
      transition: 'box-shadow 0.2s, transform 0.2s',
    }}
    onMouseEnter={e => {
      const el = e.currentTarget as HTMLDivElement
      el.style.boxShadow = 'var(--shadow-md)'
      el.style.transform = 'translateY(-2px)'
    }}
    onMouseLeave={e => {
      const el = e.currentTarget as HTMLDivElement
      el.style.boxShadow = 'var(--shadow-sm)'
      el.style.transform = 'translateY(0)'
    }}
    >
      {/* vermilion accent bar */}
      <div style={{ height: '3px', background: 'var(--accent)' }} />

      <div style={{ padding: '1.1rem 1.35rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          {/* rank badge */}
          <span style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--gold)',
          }}>
            #{index + 1}
          </span>

          {/* match score pill */}
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2px 10px',
            borderRadius: '99px',
            background: scoreBg,
            color: scoreColor,
            fontSize: '0.82rem',
            fontWeight: 700,
            border: `1px solid ${scoreColor}33`,
          }}>
            {score}%
            <span style={{ fontSize: '0.65rem', fontWeight: 400, opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.04em' }}> match</span>
          </span>
        </div>

        <h3 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '1.05rem',
          fontWeight: 700,
          color: 'var(--ink)',
          marginBottom: '0.4rem',
          lineHeight: 1.3,
        }}>
          {rec.title}
        </h3>

        <p style={{
          fontSize: '0.855rem',
          color: 'var(--muted)',
          lineHeight: 1.65,
          margin: 0,
        }}>
          {rec.reason}
        </p>
      </div>
    </div>
  )
}
