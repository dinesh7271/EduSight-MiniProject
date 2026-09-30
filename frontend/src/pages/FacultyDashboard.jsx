import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import NavBar from '../components/NavBar'
import RiskBadge from '../components/RiskBadge'
import ShapChart from '../components/ShapChart'
import ActionChecklist from '../components/ActionChecklist'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const DEFAULT_FEATURES = {
  window: 'week12',
  Marital_status: 1, Application_mode: 1, Application_order: 1, Course: 33,
  Daytime_evening_attendance: 1, Previous_qualification: 1,
  Previous_qualification_grade: 122, Nacionality: 1,
  Mothers_qualification: 2, Fathers_qualification: 2,
  Mothers_occupation: 10, Fathers_occupation: 10,
  Displaced: 0, Educational_special_needs: 0, Debtor: 0,
  Tuition_fees_up_to_date: 1, Gender: 1, Scholarship_holder: 0,
  Age_at_enrollment: 20, International: 0,
  Curricular_units_1st_sem_credited: 0, Curricular_units_1st_sem_enrolled: 6,
  Curricular_units_1st_sem_evaluations: 6, Curricular_units_1st_sem_approved: 4,
  Curricular_units_1st_sem_grade: 11.5, Curricular_units_1st_sem_without_evaluations: 0,
  Curricular_units_2nd_sem_credited: 0, Curricular_units_2nd_sem_enrolled: 6,
  Curricular_units_2nd_sem_evaluations: 5, Curricular_units_2nd_sem_approved: 3,
  Curricular_units_2nd_sem_grade: 10.0, Curricular_units_2nd_sem_without_evaluations: 1,
  GDP: 1.74, Inflation_rate: 1.4, Unemployment_rate: 10.8,
}

function StatCard({ value, label, className }) {
  return (
    <div className={`stat-card ${className}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  )
}

function RiskBadgeSmall({ level }) {
  const cfg = {
    high: { class: 'badge-high', text: 'HIGH' },
    medium: { class: 'badge-medium', text: 'MED' },
    low: { class: 'badge-low', text: 'LOW' },
    unknown: { class: '', text: 'N/A' },
  }
  const c = cfg[level] || cfg.unknown
  return <span className={`badge ${c.class}`}>{c.text}</span>
}

function StudentDrawer({ student, onClose, onInterventionSaved }) {
  const [explanation, setExplanation] = useState(null)
  const [actionPlan, setActionPlan] = useState(null)
  const [interventions, setInterventions] = useState([])
  const [loadingData, setLoadingData] = useState(true)
  const [notes, setNotes] = useState('')
  const [action, setAction] = useState('Counseling session scheduled')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    async function fetchDetails() {
      if (!student?.student_id) return
      setLoadingData(true)
      const payload = { student_id: student.student_id, features: DEFAULT_FEATURES }
      const [explRes, recRes, ivRes] = await Promise.allSettled([
        client.post('/api/explain', payload),
        client.post('/api/recommend', payload),
        client.get(`/api/interventions/${student.student_id}`),
      ])
      if (explRes.status === 'fulfilled') setExplanation(explRes.value.data)
      if (recRes.status === 'fulfilled') setActionPlan(recRes.value.data)
      if (ivRes.status === 'fulfilled') setInterventions(ivRes.value.data)
      setLoadingData(false)
    }
    fetchDetails()
  }, [student])

  async function handleSaveIntervention() {
    if (!notes.trim()) return
    setSaving(true)
    try {
      await client.post('/api/interventions', {
        student_id: student.student_id,
        action_taken: action,
        notes,
      })
      setSaved(true)
      setNotes('')
      onInterventionSaved && onInterventionSaved()
      // Refresh interventions
      const res = await client.get(`/api/interventions/${student.student_id}`)
      setInterventions(res.data)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Failed to save intervention')
    } finally {
      setSaving(false)
    }
  }

  const pred = student?.latest_prediction
  const riskLevel = pred?.risk_level || 'unknown'

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-drawer">
        <div className="modal-header">
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {student?.username}
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 2 }}>
              ID: {student?.student_id}
            </p>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Risk summary */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          padding: '16px 20px',
          borderRadius: 12,
          background: riskLevel === 'high' ? 'var(--risk-high-bg)' :
                      riskLevel === 'medium' ? 'var(--risk-medium-bg)' :
                      'var(--risk-low-bg)',
          marginBottom: 24,
        }}>
          <RiskBadge
            probability={pred?.risk_probability}
            level={riskLevel}
            size="sm"
          />
          <div>
            <RiskBadgeSmall level={riskLevel} />
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
              {pred?.created_at
                ? new Date(pred.created_at).toLocaleDateString()
                : 'No prediction yet'}
            </div>
          </div>
        </div>

        {loadingData ? (
          <div>
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton skeleton-card" style={{ marginBottom: 12 }} />
            ))}
          </div>
        ) : (
          <>
            {/* SHAP factors */}
            {explanation?.top_factors?.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <div className="section-title" style={{ marginBottom: 12 }}>
                  Contributing Factors
                </div>
                <ShapChart contributions={explanation.top_factors} maxItems={4} />
              </div>
            )}

            {/* Action plan */}
            {actionPlan?.steps?.length > 0 && (
              <div style={{ marginBottom: 24 }}>
                <div className="section-title" style={{ marginBottom: 12 }}>
                  Recommended Actions
                </div>
                <ActionChecklist steps={actionPlan.steps} />
              </div>
            )}

            <div className="divider" />

            {/* Intervention form */}
            <div style={{ marginBottom: 20 }}>
              <div className="section-title" style={{ marginBottom: 14 }}>
                Record Intervention
              </div>

              {saved && (
                <div className="success-message">✓ Intervention recorded successfully.</div>
              )}

              <div className="form-group">
                <label className="form-label">Action Taken</label>
                <select
                  className="select-field"
                  value={action}
                  onChange={e => setAction(e.target.value)}
                >
                  <option>Counseling session scheduled</option>
                  <option>Parent/Guardian contacted</option>
                  <option>Study plan created</option>
                  <option>Referred to support services</option>
                  <option>Discussed performance with student</option>
                  <option>Follow-up meeting scheduled</option>
                  <option>Other</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <textarea
                  className="textarea-field"
                  placeholder="Add notes about this intervention…"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                />
              </div>

              <button
                className="btn btn-primary btn-full"
                onClick={handleSaveIntervention}
                disabled={saving || !notes.trim()}
              >
                {saving ? 'Saving…' : 'Save Intervention'}
              </button>
            </div>

            {/* Past interventions */}
            {interventions.length > 0 && (
              <div>
                <div className="section-title" style={{ marginBottom: 12 }}>
                  Past Interventions ({interventions.length})
                </div>
                {interventions.map(iv => (
                  <div key={iv.id} style={{
                    padding: '12px 14px',
                    borderRadius: 8,
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-light)',
                    marginBottom: 8,
                  }}>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{iv.action_taken}</div>
                    {iv.notes && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                        {iv.notes}
                      </p>
                    )}
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
                      {new Date(iv.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function FacultyDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [cohort, setCohort] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('risk_desc')
  const [selectedStudent, setSelectedStudent] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    setLoading(true)
    try {
      const [cohortRes, studentsRes] = await Promise.allSettled([
        client.get('/api/cohort'),
        client.get('/api/cohort/students'),
      ])
      if (cohortRes.status === 'fulfilled') setCohort(cohortRes.value.data)
      if (studentsRes.status === 'fulfilled') setStudents(studentsRes.value.data)
    } catch {
      // Silently handle — empty state will show
    } finally {
      setLoading(false)
    }
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  // Filter and sort students
  const filteredStudents = students
    .filter(s => {
      const q = searchQuery.toLowerCase()
      return (
        s.username?.toLowerCase().includes(q) ||
        s.student_id?.toLowerCase().includes(q)
      )
    })
    .sort((a, b) => {
      const pa = a.latest_prediction?.risk_probability ?? -1
      const pb = b.latest_prediction?.risk_probability ?? -1
      return sortBy === 'risk_desc' ? pb - pa : pa - pb
    })

  const riskChartData = [
    { name: 'Low Risk', count: cohort?.low_risk || 0, fill: '#27AE60' },
    { name: 'Medium Risk', count: cohort?.medium_risk || 0, fill: '#E67E22' },
    { name: 'High Risk', count: cohort?.high_risk || 0, fill: '#C0392B' },
  ]

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <NavBar
        userName={user?.username || 'Faculty'}
        role="FACULTY"
        onLogout={handleLogout}
      />

      <div className="page-container">
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Faculty Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: 4 }}>
            Class overview — all figures require human review before any action is taken
          </p>
        </div>

        {loading ? (
          <div className="grid-4" style={{ marginBottom: 20 }}>
            {[1,2,3,4].map(i => (
              <div key={i} className="skeleton skeleton-card" style={{ height: 90 }} />
            ))}
          </div>
        ) : (
          <>
            {/* Stats row */}
            <div className="grid-4" style={{ marginBottom: 20 }}>
              <StatCard value={cohort?.total_students ?? 0} label="Total Students" className="total" />
              <StatCard value={cohort?.low_risk ?? 0} label="Low Risk" className="low" />
              <StatCard value={cohort?.medium_risk ?? 0} label="Medium Risk" className="medium" />
              <StatCard value={cohort?.high_risk ?? 0} label="High Risk" className="high" />
            </div>

            {/* Charts + Table */}
            <div className="grid-2" style={{ marginBottom: 20, alignItems: 'start' }}>

              {/* Risk distribution chart */}
              <div className="card">
                <div className="card-title" style={{ marginBottom: 16 }}>
                  Risk Distribution
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={riskChartData} margin={{ top: 4, right: 8, left: -20, bottom: 4 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                      {riskChartData.map((d, i) => (
                        <Cell key={i} fill={d.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Quick info */}
              <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="card-title">Class Summary</div>
                {cohort ? (
                  <>
                    <div style={{ padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
                      <div style={{ fontWeight: 700, color: 'var(--risk-high)', fontSize: '1.5rem' }}>
                        {cohort.high_risk}
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        students flagged as high risk
                      </div>
                    </div>
                    <div className="disclaimer">
                      These predictions are model-based estimates.
                      Review each student's situation individually before intervening.
                    </div>
                  </>
                ) : (
                  <div className="empty-state">
                    <p>No data available. Ensure students have predictions.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Student table */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Student List</div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <div className="search-input-wrap">
                    <span className="search-icon" style={{ fontSize: '0.9rem' }}>🔍</span>
                    <input
                      type="text"
                      className="input-field"
                      style={{ width: 200, padding: '8px 12px 8px 34px' }}
                      placeholder="Search students…"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <select
                    className="select-field"
                    style={{ width: 160, padding: '8px 12px' }}
                    value={sortBy}
                    onChange={e => setSortBy(e.target.value)}
                  >
                    <option value="risk_desc">Highest Risk First</option>
                    <option value="risk_asc">Lowest Risk First</option>
                  </select>
                </div>
              </div>

              {filteredStudents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-state-icon">👥</div>
                  <div className="empty-state-title">No students found</div>
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Risk Level</th>
                        <th onClick={() => setSortBy(s => s === 'risk_desc' ? 'risk_asc' : 'risk_desc')}
                            style={{ cursor: 'pointer' }}>
                          Risk % ↕
                        </th>
                        <th>Last Prediction</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredStudents.map(student => {
                        const pred = student.latest_prediction
                        const level = pred?.risk_level || 'unknown'
                        return (
                          <tr key={student.id}>
                            <td>
                              <div style={{ fontWeight: 600 }}>{student.username}</div>
                              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                {student.student_id}
                              </div>
                            </td>
                            <td><RiskBadgeSmall level={level} /></td>
                            <td>
                              <span style={{
                                fontWeight: 700,
                                color: level === 'high' ? 'var(--risk-high)' :
                                       level === 'medium' ? 'var(--risk-medium)' :
                                       'var(--risk-low)',
                              }}>
                                {pred ? `${Math.round(pred.risk_probability * 100)}%` : '—'}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                              {pred?.created_at
                                ? new Date(pred.created_at).toLocaleDateString()
                                : '—'}
                            </td>
                            <td>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => setSelectedStudent(student)}
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Student detail drawer */}
      {selectedStudent && (
        <StudentDrawer
          student={selectedStudent}
          onClose={() => setSelectedStudent(null)}
          onInterventionSaved={fetchData}
        />
      )}
    </div>
  )
}
