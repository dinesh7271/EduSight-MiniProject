/**
 * RiskBadge — Circular gauge showing risk probability.
 * Props:
 *   probability: 0-1
 *   level: 'low' | 'medium' | 'high' | 'unknown'
 *   size: 'sm' | 'md' | 'lg'
 */
export default function RiskBadge({ probability, level, size = 'lg' }) {
  const dimensions = { sm: 80, md: 110, lg: 140 }
  const dim = dimensions[size] || 140
  const radius = (dim - 16) / 2
  const circumference = 2 * Math.PI * radius
  const pct = typeof probability === 'number' ? Math.max(0, Math.min(1, probability)) : 0
  const offset = circumference - pct * circumference

  const colors = {
    high: '#C0392B',
    medium: '#E67E22',
    low: '#27AE60',
    unknown: '#D4C5A9',
  }
  const color = colors[level] || colors.unknown

  const textSizes = { sm: '1.1rem', md: '1.5rem', lg: '2rem' }
  const labelSizes = { sm: '0.6rem', md: '0.65rem', lg: '0.7rem' }

  const levelLabels = {
    high: 'HIGH RISK',
    medium: 'MEDIUM RISK',
    low: 'LOW RISK',
    unknown: 'NO DATA',
  }

  return (
    <div className="risk-circle-container">
      <div className="risk-circle" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`}>
          {/* Track ring */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke="#EDE4D4"
            strokeWidth="10"
          />
          {/* Progress ring */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        {/* Center content */}
        <div className="risk-circle-value">
          <span
            className="risk-pct"
            style={{ color, fontSize: textSizes[size] }}
          >
            {probability != null ? `${Math.round(pct * 100)}%` : '—'}
          </span>
          <span
            className="risk-label-text"
            style={{ color, fontSize: labelSizes[size] }}
          >
            {levelLabels[level] || 'RISK'}
          </span>
        </div>
      </div>
    </div>
  )
}
