import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'

// SVG Icons
function GradCapIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
      <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3z" fill="white" />
      <path d="M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" fill="white" opacity="0.85" />
    </svg>
  )
}

function StudentIcon({ active }) {
  return (
    <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" fill={active ? '#6B9E78' : '#D4C5A9'} />
      <path d="M4 20c0-4 3.58-7 8-7s8 3 8 7" fill={active ? '#6B9E78' : '#D4C5A9'} opacity="0.75" />
    </svg>
  )
}

function TeacherIcon({ active }) {
  return (
    <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="3" width="18" height="13" rx="2" fill={active ? '#6B9E78' : '#D4C5A9'} opacity="0.5" />
      <path d="M2 13h18M8 18h8" stroke={active ? '#6B9E78' : '#D4C5A9'} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="7" cy="8" r="2" fill={active ? '#6B9E78' : '#D4C5A9'} />
      <path d="M11 7h6M11 10h4" stroke={active ? '#6B9E78' : '#D4C5A9'} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function EyeIcon({ visible }) {
  return visible ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export default function LoginPage() {
  const [mode, setMode] = useState('login') // 'login' or 'register'
  const [selectedRole, setSelectedRole] = useState('STUDENT') // 'STUDENT' or 'FACULTY'
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()

  function handleRoleChange(role) {
    setSelectedRole(role)
    setError('')
  }

  function handleModeChange(newMode) {
    setMode(newMode)
    setError('')
    setSuccess('')
  }

  function handleQuickFill(demoUser, demoPass, demoRole) {
    setUsername(demoUser)
    setPassword(demoPass)
    setSelectedRole(demoRole)
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')

    const cleanUser = username.trim()
    if (!cleanUser) {
      setError('Please enter a username.')
      return
    }
    if (!password) {
      setError('Please enter a password.')
      return
    }

    if (mode === 'register') {
      if (cleanUser.length < 3) {
        setError('Username must be at least 3 characters long.')
        return
      }
      if (password.length < 4) {
        setError('Password must be at least 4 characters long.')
        return
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.')
        return
      }
    }

    setLoading(true)
    try {
      if (mode === 'login') {
        // Sign In
        const res = await client.post('/api/auth/login', {
          username: cleanUser,
          password: password,
        })
        const { access_token, role, username: uname, student_id } = res.data
        login(access_token, { role, username: uname, student_id })

        if (role === 'FACULTY') navigate('/faculty')
        else if (role === 'ADMIN') navigate('/admin')
        else navigate('/dashboard')
      } else {
        // Create Account
        const res = await client.post('/api/auth/register', {
          username: cleanUser,
          email: email.trim() || undefined,
          password: password,
          role: selectedRole,
        })
        const { access_token, role, username: uname, student_id } = res.data
        login(access_token, { role, username: uname, student_id })

        if (role === 'FACULTY') navigate('/faculty')
        else if (role === 'ADMIN') navigate('/admin')
        else navigate('/dashboard')
      }
    } catch (err) {
      if (!err.response) {
        setError('Cannot connect to the EduSight API server. Please verify the backend is running on http://localhost:8000.')
      } else {
        const detail = err.response?.data?.detail
        if (typeof detail === 'string') {
          setError(detail)
        } else if (Array.isArray(detail)) {
          setError(detail.map(d => d.msg || d).join(', '))
        } else {
          setError(mode === 'login' ? 'Invalid credentials. Please try again.' : 'Registration failed. Please try another username.')
        }
      }
    } finally {
      setLoading(false)
    }
  }

  const roleCards = [
    { id: 'STUDENT', label: 'Student', hint: 'View your risk & action recommendations' },
    { id: 'FACULTY', label: 'Teacher / Faculty', hint: 'Monitor class cohorts & record advisor interventions' },
  ]

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '32px 16px',
    }}>
      <div style={{ width: '100%', maxWidth: 480 }}>

        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 68,
            height: 68,
            background: 'var(--accent)',
            borderRadius: 18,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 14px',
            boxShadow: '0 4px 16px rgba(107, 158, 120, 0.35)',
          }}>
            <GradCapIcon />
          </div>
          <h1 style={{
            fontSize: '1.9rem',
            fontWeight: 800,
            color: 'var(--accent)',
            letterSpacing: '-0.03em',
            marginBottom: 4,
          }}>
            EduSight
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            AI-Powered Academic Early Warning & Decision Support
          </p>
        </div>

        {/* Auth Card */}
        <div className="card" style={{ padding: '32px 28px' }}>
          
          {/* Tab Navigation: Sign In vs Create Account */}
          <div style={{
            display: 'flex',
            borderBottom: '2px solid var(--border-light)',
            marginBottom: 24,
          }}>
            <button
              type="button"
              onClick={() => handleModeChange('login')}
              style={{
                flex: 1,
                padding: '10px 0',
                background: 'none',
                border: 'none',
                borderBottom: mode === 'login' ? '3px solid var(--accent)' : '3px solid transparent',
                marginBottom: -2,
                cursor: 'pointer',
                fontWeight: mode === 'login' ? 700 : 500,
                fontSize: '1rem',
                color: mode === 'login' ? 'var(--accent)' : 'var(--text-secondary)',
                transition: 'all 0.15s ease',
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('register')}
              style={{
                flex: 1,
                padding: '10px 0',
                background: 'none',
                border: 'none',
                borderBottom: mode === 'register' ? '3px solid var(--accent)' : '3px solid transparent',
                marginBottom: -2,
                cursor: 'pointer',
                fontWeight: mode === 'register' ? 700 : 500,
                fontSize: '1rem',
                color: mode === 'register' ? 'var(--accent)' : 'var(--text-secondary)',
                transition: 'all 0.15s ease',
              }}
            >
              Create Account
            </button>
          </div>

          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 16, color: 'var(--text-primary)' }}>
            {mode === 'login' ? 'Sign in to your account' : 'Register for EduSight'}
          </h2>

          {/* Role selector */}
          <div style={{ marginBottom: 20 }}>
            <label className="form-label" style={{ marginBottom: 8 }}>
              {mode === 'login' ? 'Select your role' : 'I am registering as'}
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {roleCards.map(rc => {
                const isSelected = selectedRole === rc.id
                return (
                  <button
                    key={rc.id}
                    type="button"
                    onClick={() => handleRoleChange(rc.id)}
                    style={{
                      padding: '14px 10px',
                      border: `2px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                      borderRadius: 10,
                      background: isSelected ? 'var(--accent-light)' : 'var(--bg-secondary)',
                      cursor: 'pointer',
                      textAlign: 'center',
                      transition: 'all 0.18s ease',
                    }}
                  >
                    <div style={{ marginBottom: 6 }}>
                      {rc.id === 'STUDENT'
                        ? <StudentIcon active={isSelected} />
                        : <TeacherIcon active={isSelected} />
                      }
                    </div>
                    <div style={{
                      fontWeight: 700,
                      fontSize: '0.88rem',
                      color: isSelected ? 'var(--accent)' : 'var(--text-secondary)',
                      marginBottom: 2,
                    }}>
                      {rc.label}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.2 }}>
                      {rc.hint}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            {error && (
              <div className="error-message" style={{ marginBottom: 16, lineHeight: 1.4 }}>
                <strong>Error: </strong> {error}
              </div>
            )}
            {success && (
              <div className="success-message" style={{ marginBottom: 16 }}>
                {success}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                type="text"
                className="input-field"
                placeholder={mode === 'login' ? 'Enter your username' : 'Choose a unique username'}
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>

            {mode === 'register' && (
              <div className="form-group">
                <label className="form-label">Email Address (Optional)</label>
                <input
                  type="email"
                  className="input-field"
                  placeholder="your.email@institution.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="input-with-icon">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder={mode === 'login' ? 'Enter your password' : 'Create a secure password (min 4 chars)'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  required
                />
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => setShowPassword(v => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  <EyeIcon visible={showPassword} />
                </button>
              </div>
            </div>

            {mode === 'register' && (
              <div className="form-group">
                <label className="form-label">Confirm Password</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input-field"
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary btn-full"
              style={{ marginTop: 8, padding: '13px 20px', fontSize: '0.98rem' }}
              disabled={loading}
            >
              {loading ? (mode === 'login' ? 'Signing in…' : 'Creating account…') : (mode === 'login' ? 'Sign In' : 'Create Account')}
            </button>
          </form>

          {/* Mode switch link */}
          <div style={{ textAlign: 'center', marginTop: 18, fontSize: '0.88rem' }}>
            {mode === 'login' ? (
              <span style={{ color: 'var(--text-secondary)' }}>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleModeChange('register')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--accent)',
                    fontWeight: 700,
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Create Account
                </button>
              </span>
            ) : (
              <span style={{ color: 'var(--text-secondary)' }}>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => handleModeChange('login')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--accent)',
                    fontWeight: 700,
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  Sign In
                </button>
              </span>
            )}
          </div>

          {/* Quick Demo Fill Buttons (when in login mode) */}
          {mode === 'login' && (
            <div style={{
              marginTop: 24,
              padding: '14px 16px',
              background: 'var(--bg-secondary)',
              borderRadius: 10,
              fontSize: '0.82rem',
              border: '1px solid var(--border-light)',
            }}>
              <p style={{ fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>
                ⚡ Quick Demo Logins
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleQuickFill('student1', 'student123', 'STUDENT')}
                >
                  Fill Student (student1)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleQuickFill('faculty1', 'faculty123', 'FACULTY')}
                >
                  Fill Teacher (faculty1)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleQuickFill('admin', 'admin123', 'FACULTY')}
                >
                  Fill Admin (admin)
                </button>
              </div>
            </div>
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 18 }}>
          EduSight Decision Support · Model estimates require human educator review
        </p>
      </div>
    </div>
  )
}
