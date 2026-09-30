import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList
} from 'recharts'

/**
 * ShapChart — Horizontal bar chart of SHAP contributions.
 * Props:
 *   contributions: Array of { feature_label, shap_value, direction }
 *   maxItems: number (default 5)
 */
export default function ShapChart({ contributions = [], maxItems = 5 }) {
  const data = contributions
    .slice(0, maxItems)
    .map(c => ({
      name: c.feature_label || c.feature,
      value: Math.abs(c.shap_value),
      direction: c.direction,
      raw: c.shap_value,
    }))
    .sort((a, b) => b.value - a.value)

  if (data.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <p>No SHAP data available yet.</p>
      </div>
    )
  }

  const getColor = (direction) =>
    direction === 'increases_risk' ? '#C0392B' : '#27AE60'

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload
      return (
        <div style={{
          background: '#fff',
          border: '1px solid #D4C5A9',
          borderRadius: 8,
          padding: '10px 14px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          fontSize: '0.85rem',
        }}>
          <p style={{ fontWeight: 700, marginBottom: 4 }}>{d.name}</p>
          <p style={{ color: getColor(d.direction) }}>
            {d.direction === 'increases_risk' ? '↑ Increases risk' : '↓ Decreases risk'}
          </p>
          <p style={{ color: '#5A5A5A' }}>
            SHAP value: {d.raw > 0 ? '+' : ''}{d.raw.toFixed(4)}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(data.length * 52, 150)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 24, bottom: 4, left: 0 }}
        >
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: '#8A8A8A' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={180}
            tick={{ fontSize: 12, fill: '#2D2D2D' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={22}>
            {data.map((entry, index) => (
              <Cell key={index} fill={getColor(entry.direction)} opacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: '0.8rem' }}>
        <span style={{ color: '#27AE60', fontWeight: 600 }}>
          ■ Decreases predicted risk
        </span>
        <span style={{ color: '#C0392B', fontWeight: 600 }}>
          ■ Increases predicted risk
        </span>
      </div>
    </div>
  )
}
