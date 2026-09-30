import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import NavBar from '../components/NavBar'
import RiskBadge from '../components/RiskBadge'
import ShapChart from '../components/ShapChart'
import ActionChecklist from '../components/ActionChecklist'

function SkeletonCard({ height = 120 }) {
  return (
    <div className="card" style={{ minHeight: height }}>
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-text" />
      <div className="skeleton skeleton-text" style={{ width: '80%' }} />
    </div>
  )
}

export default function StudentDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState('')
  const [hasExistingPrediction, setHasExistingPrediction] = useState(false)
  const [isFormOpen, setIsFormOpen] = useState(false)

  const [prediction, setPrediction] = useState(null)
  const [explanation, setExplanation] = useState(null)
  const [actionPlan, setActionPlan] = useState(null)

  // Current Semester Academic Inputs
  const [semesterData, setSemesterData] = useState({
    stage: 'week12', // 'week4' (early), 'week8' (mid-term / post CIA-1), 'week12' (late-term / post CIA-2)
    attendancePct: 82, // 0 - 100%
    internal1Marks: 65, // out of 100
    internal2Marks: 60, // out of 100
    totalSubjects: 6, // number of subjects enrolled this semester
    subjectsCleared: 5, // number of subjects passed/cleared
    assignmentsCompleted: 6, // assignments & lab tests submitted
    hasArrears: 0, // 0 = No arrears/backlogs, 1 = Has backlogs
    feesPaid: 1, // 1 = Fees paid, 0 = Pending/overdue
    prevCgpa: 7.5, // 0.0 - 10.0 scale
    attendanceShift: 'Daytime', // Daytime vs Evening
    hasScholarship: 0, // 1 = Yes, 0 = No
    age: 20,
  })

  useEffect(() => {
    loadStudentData()
  }, [user?.student_id])

  async function getStudentId() {
    let currentId = user?.student_id
    if (!currentId) {
      try {
        const meRes = await client.get('/api/students/me')
        currentId = meRes.data?.student_id
      } catch {
        currentId = 'student-001'
      }
    }
    return currentId || 'student-001'
  }

  async function loadStudentData() {
    setLoading(true)
    setError('')
    try {
      const currentId = await getStudentId()

      const historyRes = await client.get(`/api/predictions/${currentId}`)
      const pastPreds = historyRes.data || []

      if (pastPreds.length > 0) {
        const latest = pastPreds[0]
        setPrediction(latest)
        setHasExistingPrediction(true)
        setIsFormOpen(false)

        // If saved features exist, restore student inputs
        if (latest.features_used) {
          const f = latest.features_used
          setSemesterData(prev => ({
            ...prev,
            stage: latest.window || 'week12',
            internal1Marks: f.Curricular_units_1st_sem_grade ? Math.round((f.Curricular_units_1st_sem_grade / 20) * 100) : prev.internal1Marks,
            internal2Marks: f.Curricular_units_2nd_sem_grade ? Math.round((f.Curricular_units_2nd_sem_grade / 20) * 100) : prev.internal2Marks,
            totalSubjects: f.Curricular_units_1st_sem_enrolled || prev.totalSubjects,
            subjectsCleared: f.Curricular_units_1st_sem_approved || prev.subjectsCleared,
            assignmentsCompleted: f.Curricular_units_1st_sem_evaluations || prev.assignmentsCompleted,
            feesPaid: f.Tuition_fees_up_to_date ?? 1,
            hasArrears: f.Debtor ?? 0,
            hasScholarship: f.Scholarship_holder ?? 0,
          }))
        }

        // Fetch explanation & recourse for latest prediction
        const payload = {
          student_id: currentId,
          features: { window: latest.window || 'week12', ...(latest.features_used || {}) },
        }
        const [explRes, recRes] = await Promise.allSettled([
          client.post('/api/explain', payload),
          client.post('/api/recommend', payload),
        ])
        if (explRes.status === 'fulfilled') setExplanation(explRes.value.data)
        if (recRes.status === 'fulfilled') setActionPlan(recRes.value.data)
      } else {
        // Brand new student: no evaluation yet!
        setHasExistingPrediction(false)
        setPrediction(null)
        setExplanation(null)
        setActionPlan(null)
        setIsFormOpen(true)
      }
    } catch (err) {
      console.warn('Could not load student prediction history:', err)
      setHasExistingPrediction(false)
      setIsFormOpen(true)
    } finally {
      setLoading(false)
    }
  }

  function handleFieldChange(field, val) {
    setSemesterData(prev => ({
      ...prev,
      [field]: val,
    }))
  }

  async function handleCalculateAssessment(e) {
    e.preventDefault()
    setCalculating(true)
    setError('')

    // Validate inputs
    if (semesterData.attendancePct < 0 || semesterData.attendancePct > 100) {
      setError('Attendance Percentage must be between 0% and 100%.')
      setCalculating(false)
      return
    }
    if (semesterData.internal1Marks < 0 || semesterData.internal1Marks > 100) {
      setError('Internal Assessment 1 Marks must be between 0 and 100.')
      setCalculating(false)
      return
    }
    if (semesterData.stage === 'week12' && (semesterData.internal2Marks < 0 || semesterData.internal2Marks > 100)) {
      setError('Internal Assessment 2 Marks must be between 0 and 100.')
      setCalculating(false)
      return
    }

    try {
      const currentId = await getStudentId()

      // Convert semester inputs to the machine learning feature representation
      // Internal marks scale: (marks / 100) * 20 (0 - 20 scale)
      const g1 = (semesterData.internal1Marks / 100) * 20
      const g2 = (semesterData.internal2Marks / 100) * 20
      const enrolled = Number(semesterData.totalSubjects)
      const approved = Number(semesterData.subjectsCleared)
      const evals = Number(semesterData.assignmentsCompleted)

      const featuresPayload = {
        window: semesterData.stage,
        Curricular_units_1st_sem_enrolled: enrolled,
        Curricular_units_1st_sem_approved: approved,
        Curricular_units_1st_sem_evaluations: evals,
        Curricular_units_1st_sem_grade: g1,
        Curricular_units_2nd_sem_enrolled: enrolled,
        Curricular_units_2nd_sem_approved: Math.max(0, approved),
        Curricular_units_2nd_sem_evaluations: evals,
        Curricular_units_2nd_sem_grade: g2,
        'Daytime/evening_attendance': semesterData.attendanceShift === 'Daytime' ? 1 : 0,
        Tuition_fees_up_to_date: Number(semesterData.feesPaid),
        Debtor: Number(semesterData.hasArrears),
        Scholarship_holder: Number(semesterData.hasScholarship),
        Admission_grade: 125.0,
        Previous_qualification_grade: Math.min(200, (Number(semesterData.prevCgpa) / 10) * 200),
        Age_at_enrollment: Number(semesterData.age),
      }

      const payload = {
        student_id: currentId,
        features: featuresPayload,
      }

      const [predRes, explRes, recRes] = await Promise.allSettled([
        client.post('/api/predict', payload),
        client.post('/api/explain', payload),
        client.post('/api/recommend', payload),
      ])

      if (predRes.status === 'fulfilled') {
        setPrediction(predRes.value.data)
        setHasExistingPrediction(true)
        setIsFormOpen(false)
      } else {
        const detail = predRes.reason?.response?.data?.detail
        throw new Error(detail || 'Failed to calculate risk assessment.')
      }

      if (explRes.status === 'fulfilled') setExplanation(explRes.value.data)
      if (recRes.status === 'fulfilled') setActionPlan(recRes.value.data)
    } catch (err) {
      setError(err.message || 'Error communicating with prediction server.')
    } finally {
      setCalculating(false)
    }
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const riskColors = {
    high: 'var(--risk-high)',
    medium: 'var(--risk-medium)',
    low: 'var(--risk-low)',
    unknown: 'var(--text-muted)',
  }
  const riskLevel = prediction?.risk_level || 'unknown'

  const att = Number(semesterData.attendancePct)
  const isAttendanceShortage = att < 75

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <NavBar
        userName={user?.username || 'Student'}
        role="STUDENT"
        onLogout={handleLogout}
      />

      <div className="page-container">
        {/* Header with Title & Action Button */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 24,
        }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Current Semester Academic Performance Predictor
            </h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: '0.9rem' }}>
              Evaluates current attendance, internal marks, assignment completion, and arrears for this semester
            </p>
          </div>

          {hasExistingPrediction && (
            <button
              className="btn btn-secondary"
              onClick={() => setIsFormOpen(prev => !prev)}
            >
              {isFormOpen ? '✕ Close Form' : '✏️ Update Semester Marks & Attendance'}
            </button>
          )}
        </div>

        {error && (
          <div className="error-message" style={{ marginBottom: 20 }}>
            ⚠ {error}
          </div>
        )}

        {loading ? (
          <div>
            <div className="grid-2" style={{ marginBottom: 20 }}>
              <SkeletonCard height={200} />
              <SkeletonCard height={200} />
            </div>
            <SkeletonCard height={240} />
          </div>
        ) : (
          <>
            {/* NEW STUDENT WELCOME (if no prediction has been submitted yet) */}
            {!hasExistingPrediction && !prediction && (
              <div style={{
                background: 'var(--bg-card)',
                border: '1.5px solid var(--border)',
                borderRadius: 12,
                padding: '22px 26px',
                marginBottom: 24,
                boxShadow: 'var(--shadow-sm)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <span style={{ fontSize: '2rem' }}>📊</span>
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent)' }}>
                      Welcome, {user?.username}! Enter your semester records to predict performance.
                    </h3>
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: 3 }}>
                      To evaluate your risk for this semester, enter your <strong>Attendance Percentage</strong>, <strong>Internal Assessment Marks (CIA 1 & CIA 2)</strong>, and <strong>Assignment counts</strong> in the form below.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* SEMESTER INPUT FORM */}
            {isFormOpen && (
              <div className="card" style={{ marginBottom: 28, border: '2px solid var(--accent)' }}>
                <div className="card-header" style={{ marginBottom: 16 }}>
                  <div>
                    <h2 className="card-title">
                      {hasExistingPrediction ? 'Update This Semester’s Academic Records' : 'Enter Your Current Semester Academic Details'}
                    </h2>
                    <p className="card-subtitle">
                      Your attendance, internal marks, and assignment completion are used by AI models to predict term outcome
                    </p>
                  </div>
                  {hasExistingPrediction && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsFormOpen(false)}
                    >
                      Cancel
                    </button>
                  )}
                </div>

                <form onSubmit={handleCalculateAssessment}>
                  
                  {/* Semester Checkpoint Stage */}
                  <div className="form-group" style={{ marginBottom: 22 }}>
                    <label className="form-label" style={{ fontWeight: 700 }}>
                      Current Semester Timeline Checkpoint
                    </label>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
                      {[
                        { id: 'week4', label: 'Week 4 (Early Term)', sub: 'Before Internal Exams (Attendance & Course load)' },
                        { id: 'week8', label: 'Week 8 (Mid-Semester)', sub: 'After Internal Assessment 1 (CIA 1)' },
                        { id: 'week12', label: 'Week 12 (Late-Semester)', sub: 'After Internal Assessment 2 (CIA 2)' },
                      ].map(s => {
                        const active = semesterData.stage === s.id
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => handleFieldChange('stage', s.id)}
                            style={{
                              padding: '12px 14px',
                              textAlign: 'left',
                              borderRadius: 8,
                              border: `2px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                              background: active ? 'var(--accent-light)' : 'var(--bg-secondary)',
                              cursor: 'pointer',
                            }}
                          >
                            <div style={{ fontWeight: 700, color: active ? 'var(--accent)' : 'var(--text-primary)' }}>
                              {s.label}
                            </div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: 2 }}>
                              {s.sub}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Section 1: Attendance & Exam Eligibility */}
                  <div style={{
                    padding: '16px 18px',
                    borderRadius: 8,
                    background: 'var(--bg-secondary)',
                    marginBottom: 18,
                    border: '1px solid var(--border-light)',
                  }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                      1. Current Attendance Rate
                    </h3>
                    <div className="grid-2">
                      <div className="form-group">
                        <label className="form-label">
                          Attendance Percentage (%)
                        </label>
                        <input
                          type="number"
                          className="input-field"
                          min="0"
                          max="100"
                          value={semesterData.attendancePct}
                          onChange={e => handleFieldChange('attendancePct', Number(e.target.value))}
                          required
                        />
                        <div style={{ marginTop: 6, fontSize: '0.8rem' }}>
                          {att >= 75 ? (
                            <span style={{ color: '#27AE60', fontWeight: 600 }}>
                              ✓ {att}% Attendance: Meets university 75% exam eligibility threshold.
                            </span>
                          ) : (
                            <span style={{ color: '#C0392B', fontWeight: 600 }}>
                              ⚠ {att}% Attendance: Below 75% minimum! Risk of exam condonation / detention.
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Attendance Shift</label>
                        <select
                          className="select-field"
                          value={semesterData.attendanceShift}
                          onChange={e => handleFieldChange('attendanceShift', e.target.value)}
                        >
                          <option value="Daytime">Daytime Classes</option>
                          <option value="Evening">Evening / Working Shift</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Section 2: Internal Assessment Marks (CIA) */}
                  <div style={{
                    padding: '16px 18px',
                    borderRadius: 8,
                    background: 'var(--bg-secondary)',
                    marginBottom: 18,
                    border: '1px solid var(--border-light)',
                  }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                      2. Internal Assessment & Exam Marks
                    </h3>

                    {semesterData.stage === 'week4' ? (
                      <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                        ℹ️ Internal exams have not taken place yet at Week 4. Prediction will be calculated based on attendance, course enrollment, and background.
                      </p>
                    ) : (
                      <div className="grid-2">
                        <div className="form-group">
                          <label className="form-label">
                            Internal Assessment 1 (CIA 1 / Midterm 1) Marks (Out of 100)
                          </label>
                          <input
                            type="number"
                            className="input-field"
                            min="0"
                            max="100"
                            value={semesterData.internal1Marks}
                            onChange={e => handleFieldChange('internal1Marks', Number(e.target.value))}
                            required
                          />
                          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                            Scale: 50+ is passing, 75+ is distinction
                          </span>
                        </div>

                        {semesterData.stage === 'week12' && (
                          <div className="form-group">
                            <label className="form-label">
                              Internal Assessment 2 (CIA 2 / Midterm 2) Marks (Out of 100)
                            </label>
                            <input
                              type="number"
                              className="input-field"
                              min="0"
                              max="100"
                              value={semesterData.internal2Marks}
                              onChange={e => handleFieldChange('internal2Marks', Number(e.target.value))}
                              required
                            />
                            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                              Second internal exam score
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Section 3: Coursework & Assignment Submissions */}
                  <div style={{
                    padding: '16px 18px',
                    borderRadius: 8,
                    background: 'var(--bg-secondary)',
                    marginBottom: 18,
                    border: '1px solid var(--border-light)',
                  }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                      3. Coursework, Subjects & Assignments
                    </h3>
                    <div className="grid-2">
                      <div className="form-group">
                        <label className="form-label">Total Subjects Enrolled This Semester</label>
                        <input
                          type="number"
                          className="input-field"
                          min="1"
                          max="12"
                          value={semesterData.totalSubjects}
                          onChange={e => handleFieldChange('totalSubjects', Number(e.target.value))}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Subjects Currently Cleared / Passing</label>
                        <input
                          type="number"
                          className="input-field"
                          min="0"
                          max={semesterData.totalSubjects}
                          value={semesterData.subjectsCleared}
                          onChange={e => handleFieldChange('subjectsCleared', Number(e.target.value))}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Assignments & Lab Evaluations Submitted</label>
                        <input
                          type="number"
                          className="input-field"
                          min="0"
                          max="20"
                          value={semesterData.assignmentsCompleted}
                          onChange={e => handleFieldChange('assignmentsCompleted', Number(e.target.value))}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Standing Arrears / Backlogs?</label>
                        <select
                          className="select-field"
                          value={semesterData.hasArrears}
                          onChange={e => handleFieldChange('hasArrears', Number(e.target.value))}
                        >
                          <option value={0}>No Backlogs / Arrears</option>
                          <option value={1}>Yes, Has Standing Backlogs</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Section 4: Academic Background & Standing */}
                  <div style={{
                    padding: '16px 18px',
                    borderRadius: 8,
                    background: 'var(--bg-secondary)',
                    marginBottom: 20,
                    border: '1px solid var(--border-light)',
                  }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                      4. Academic Standing & Fees
                    </h3>
                    <div className="grid-2">
                      <div className="form-group">
                        <label className="form-label">Previous Semester CGPA / Percentage (0 – 10)</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="10"
                          className="input-field"
                          value={semesterData.prevCgpa}
                          onChange={e => handleFieldChange('prevCgpa', Number(e.target.value))}
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Tuition Fee Status</label>
                        <select
                          className="select-field"
                          value={semesterData.feesPaid}
                          onChange={e => handleFieldChange('feesPaid', Number(e.target.value))}
                        >
                          <option value={1}>Paid / Up to Date</option>
                          <option value={0}>Overdue / Pending Payment</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Scholarship Beneficiary?</label>
                        <select
                          className="select-field"
                          value={semesterData.hasScholarship}
                          onChange={e => handleFieldChange('hasScholarship', Number(e.target.value))}
                        >
                          <option value={0}>No</option>
                          <option value={1}>Yes, Scholarship Holder</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Student Age</label>
                        <input
                          type="number"
                          min="16"
                          max="80"
                          className="input-field"
                          value={semesterData.age}
                          onChange={e => handleFieldChange('age', Number(e.target.value))}
                        />
                      </div>
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="btn btn-primary btn-full"
                    style={{ padding: '14px 20px', fontSize: '1rem' }}
                    disabled={calculating}
                  >
                    {calculating ? 'Analyzing Semester Records with AI Model…' : '🚀 Calculate My Semester Risk Assessment'}
                  </button>
                </form>
              </div>
            )}

            {/* PREDICTION RESULTS VIEW */}
            {prediction && (
              <>
                {/* Attendance Warning Alert (if < 75%) */}
                {isAttendanceShortage && (
                  <div style={{
                    padding: '14px 18px',
                    borderRadius: 10,
                    background: '#FDEDEC',
                    border: '1.5px solid var(--risk-high)',
                    marginBottom: 20,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                  }}>
                    <span style={{ fontSize: '1.6rem' }}>🚨</span>
                    <div>
                      <div style={{ fontWeight: 700, color: 'var(--risk-high)' }}>
                        Attendance Shortage Alert ({att}%)
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#5A5A5A', marginTop: 2 }}>
                        Your attendance is below the university mandatory 75% threshold. You are at high risk of being ineligible for final end-semester examinations. Contact your department advisor immediately.
                      </div>
                    </div>
                  </div>
                )}

                {/* Row 1: Risk Overview + What This Means */}
                <div className="grid-2" style={{ marginBottom: 20 }}>

                  {/* Risk Assessment Card */}
                  <div className="card">
                    <div className="card-header">
                      <div>
                        <div className="card-title">This Semester’s Risk Assessment</div>
                        <div className="card-subtitle">
                          {prediction.model_version} · Checkpoint: {prediction.window ? prediction.window.toUpperCase() : 'WEEK12'} · {
                            prediction.created_at
                              ? new Date(prediction.created_at).toLocaleDateString()
                              : 'Just now'
                          }
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '8px 0' }}>
                      <RiskBadge
                        probability={prediction.risk_probability}
                        level={riskLevel}
                        size="lg"
                      />
                    </div>

                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-around',
                      padding: '12px 14px',
                      background: 'var(--bg-secondary)',
                      borderRadius: 8,
                      marginTop: 16,
                      fontSize: '0.82rem',
                    }}>
                      <div>
                        <strong>Attendance: </strong>
                        <span style={{ color: att >= 75 ? '#27AE60' : '#C0392B', fontWeight: 700 }}>
                          {att}%
                        </span>
                      </div>
                      <div>
                        <strong>CIA 1: </strong>
                        <span style={{ fontWeight: 700 }}>{semesterData.internal1Marks}/100</span>
                      </div>
                      <div>
                        <strong>CIA 2: </strong>
                        <span style={{ fontWeight: 700 }}>{semesterData.internal2Marks}/100</span>
                      </div>
                    </div>

                    <div className="disclaimer" style={{ marginTop: 14 }}>
                      This model estimates your probability of academic difficulty for this semester based on your attendance, internal assessment scores, and coursework completion.
                    </div>
                  </div>

                  {/* What This Means */}
                  <div className="card">
                    <div className="card-title" style={{ marginBottom: 16 }}>Assessment Summary</div>

                    <div style={{
                      padding: '14px 18px',
                      borderRadius: 10,
                      background: riskLevel === 'high' ? 'var(--risk-high-bg)' :
                                  riskLevel === 'medium' ? 'var(--risk-medium-bg)' :
                                  'var(--risk-low-bg)',
                      marginBottom: 16,
                    }}>
                      <div style={{
                        fontWeight: 800,
                        fontSize: '1.1rem',
                        color: riskColors[riskLevel],
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}>
                        {riskLevel === 'high' ? '⚠ High Academic Risk' :
                         riskLevel === 'medium' ? '● Moderate Risk' :
                         '✓ Low Academic Risk'}
                      </div>
                      <p style={{ fontSize: '0.88rem', marginTop: 6, color: 'var(--text-secondary)' }}>
                        {riskLevel === 'high'
                          ? 'The system detects risk factors from your attendance and internal marks. Focus on improving upcoming test scores and attending all remaining lecture hours.'
                          : riskLevel === 'medium'
                          ? 'You are on track, but some areas need attention. Ensure all assignment deadlines are met and prepare well for the next internal assessment.'
                          : 'Your semester metrics indicate safe academic standing. Continue maintaining steady attendance and coursework submissions.'
                        }
                      </p>
                    </div>

                    {explanation?.explanation_text && (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                        <strong>Key Influences:</strong><br />
                        {explanation.explanation_text}
                      </div>
                    )}
                  </div>
                </div>

                {/* Row 2: SHAP Contributing Factors */}
                <div className="card" style={{ marginBottom: 20 }}>
                  <div className="card-header">
                    <div>
                      <div className="card-title">Influential Factors (SHAP Breakdown)</div>
                      <div className="card-subtitle">Which semester metrics had the greatest impact on this risk score?</div>
                    </div>
                  </div>

                  {explanation?.top_factors && explanation.top_factors.length > 0 ? (
                    <ShapChart contributions={explanation.top_factors} maxItems={5} />
                  ) : (
                    <div className="empty-state">
                      <div className="empty-state-title">No factor breakdown available</div>
                    </div>
                  )}

                  <div className="disclaimer" style={{ marginTop: 16 }}>
                    Red bars indicate factors that pushed your predicted risk higher; green bars indicate factors that helped protect your standing.
                  </div>
                </div>

                {/* Row 3: Action Plan */}
                <div className="card" style={{ marginBottom: 20 }}>
                  <div className="card-header">
                    <div>
                      <div className="card-title">Personalized Improvement Targets (Recourse)</div>
                      <div className="card-subtitle">Achievable semester targets to reduce your risk score</div>
                    </div>
                  </div>

                  <ActionChecklist steps={actionPlan?.steps || []} />

                  <div className="disclaimer" style={{ marginTop: 16 }}>
                    Discuss these target numbers with your class advisor or subject faculty to map out extra coaching or assignment resubmissions.
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
