/**
 * ActionChecklist — Renders recommended action steps as a checklist.
 * Props:
 *   steps: Array of ActionStep objects
 */
export default function ActionChecklist({ steps = [] }) {
  if (!steps || steps.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 24 }}>
        <p>No specific action recommendations available yet.</p>
        <p style={{ marginTop: 8, fontSize: '0.85rem' }}>
          Please consult your academic advisor for personalized guidance.
        </p>
      </div>
    )
  }

  const priorityConfig = {
    high: { label: 'HIGH', class: 'badge-high', icon: '⚡' },
    medium: { label: 'MED', class: 'badge-medium', icon: '•' },
    low: { label: 'LOW', class: 'badge-low', icon: '○' },
  }

  return (
    <div>
      {steps.map((step, i) => {
        const p = priorityConfig[step.priority] || priorityConfig.medium
        const changeDir = step.change_amount >= 0 ? '↑' : '↓'
        const changeColor = step.change_amount >= 0 ? '#27AE60' : '#C0392B'

        return (
          <div key={i} className="checklist-item">
            <div className="checklist-icon" />
            <div className="checklist-content">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span className={`badge ${p.class}`}>{p.icon} {p.label}</span>
                <span className="checklist-label">{step.feature_label}</span>
              </div>
              <div className="checklist-values">
                Current: <strong>{step.current_value}</strong>
                &nbsp;&nbsp;
                <span style={{ color: changeColor, fontWeight: 700 }}>
                  {changeDir}
                </span>
                &nbsp;&nbsp;
                Target: <strong>{step.target_value}</strong>
                {!step.feasible && (
                  <span style={{ color: '#E67E22', marginLeft: 8, fontSize: '0.78rem' }}>
                    ⚠ May need additional support
                  </span>
                )}
              </div>
              {step.note && (
                <p style={{ fontSize: '0.78rem', color: '#8A8A8A', marginTop: 3 }}>
                  {step.note}
                </p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
