import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import NavBar from '../components/NavBar'

const roleBadgeClass = {
  ADMIN: 'badge-admin',
  FACULTY: 'badge-faculty',
  STUDENT: 'badge-student',
}

export default function AdminPanel() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('overview')
  const [users, setUsers] = useState([])
  const [models, setModels] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    setLoading(true)
    const [usersRes, modelsRes, healthRes] = await Promise.allSettled([
      client.get('/api/users'),
      client.get('/api/models'),
      client.get('/api/health'),
    ])
    if (usersRes.status === 'fulfilled') setUsers(usersRes.value.data)
    if (modelsRes.status === 'fulfilled') setModels(modelsRes.value.data)
    if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data)
    setLoading(false)
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const tabStyle = (active) => ({
    padding: '10px 20px',
    border: 'none',
    borderBottom: active ? '2.5px solid var(--accent)' : '2.5px solid transparent',
    background: 'none',
    cursor: 'pointer',
    fontWeight: active ? 700 : 500,
    fontSize: '0.9rem',
    color: active ? 'var(--accent)' : 'var(--text-secondary)',
    transition: 'color 0.15s',
  })

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <NavBar userName={user?.username || 'Admin'} role="ADMIN" onLogout={handleLogout} />

      <div className="page-container">
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Admin Panel</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: 4 }}>
            System management and oversight
          </p>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-light)',
          marginBottom: 24,
          gap: 4,
        }}>
          {['overview', 'users', 'models', 'health'].map(t => (
            <button key={t} style={tabStyle(tab === t)} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <div>
            {[1, 2].map(i => (
              <div key={i} className="skeleton skeleton-card" style={{ marginBottom: 16 }} />
            ))}
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {tab === 'overview' && (
              <div className="grid-3">
                <div className="card">
                  <div className="card-title">👥 Total Users</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent)', marginTop: 8 }}>
                    {users.length}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    {users.filter(u => u.role === 'STUDENT').length} students ·{' '}
                    {users.filter(u => u.role === 'FACULTY').length} faculty ·{' '}
                    {users.filter(u => u.role === 'ADMIN').length} admins
                  </div>
                </div>

                <div className="card">
                  <div className="card-title">🤖 Models Loaded</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent)', marginTop: 8 }}>
                    {models.filter(m => m.available).length}/{models.length}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    {models.filter(m => !m.available).length > 0
                      ? `${models.filter(m => !m.available).length} window(s) not trained yet`
                      : 'All windows available'}
                  </div>
                </div>

                <div className="card">
                  <div className="card-title">⚡ System Status</div>
                  <div style={{
                    marginTop: 8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: '1.1rem',
                    fontWeight: 700,
                    color: health?.status === 'ok' ? 'var(--risk-low)' : 'var(--risk-high)',
                  }}>
                    {health?.status === 'ok' ? '✓ Online' : '⚠ Issue Detected'}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    Dataset: UCI-697 (official source)
                  </div>
                </div>
              </div>
            )}

            {/* Users Tab */}
            {tab === 'users' && (
              <div className="card">
                <div className="card-title" style={{ marginBottom: 16 }}>User Management</div>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Student ID</th>
                        <th>Status</th>
                        <th>Joined</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(u => (
                        <tr key={u.id}>
                          <td style={{ fontWeight: 600 }}>{u.username}</td>
                          <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            {u.email || '—'}
                          </td>
                          <td>
                            <span className={`badge ${roleBadgeClass[u.role] || ''}`}>
                              {u.role}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {u.student_id || '—'}
                          </td>
                          <td>
                            <span className={`badge ${u.is_active ? 'badge-low' : 'badge-high'}`}>
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Models Tab */}
            {tab === 'models' && (
              <div>
                <div className="grid-3">
                  {models.map(m => (
                    <div className="card" key={m.window}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div className="card-title">{m.window.replace('week', 'Week ')}</div>
                        <span className={`badge ${m.available ? 'badge-low' : 'badge-high'}`}>
                          {m.available ? 'Ready' : 'Not Trained'}
                        </span>
                      </div>
                      <div style={{ marginTop: 16, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <div><strong>Version:</strong> {m.model_version}</div>
                        <div><strong>Dataset:</strong> {m.dataset_id}</div>
                        {m.threshold && (
                          <div><strong>Threshold:</strong> {m.threshold.toFixed(2)}</div>
                        )}
                        {m.training_date && (
                          <div><strong>Trained:</strong> {new Date(m.training_date).toLocaleDateString()}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="card" style={{ marginTop: 20 }}>
                  <div className="card-title" style={{ marginBottom: 12 }}>Training Instructions</div>
                  <div style={{
                    background: '#1e1e2e',
                    borderRadius: 8,
                    padding: '16px 20px',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    color: '#cdd6f4',
                  }}>
                    <p style={{ color: '#a6e3a1' }}># Step 1: Download data</p>
                    <p>python -m src.data.ingestion</p>
                    <p style={{ marginTop: 8, color: '#a6e3a1' }}># Step 2: Preprocess</p>
                    <p>python -m src.preprocess</p>
                    <p style={{ marginTop: 8, color: '#a6e3a1' }}># Step 3: Train models</p>
                    <p>python -m src.models.train</p>
                    <p style={{ marginTop: 8, color: '#a6e3a1' }}># Step 4: Run API</p>
                    <p>uvicorn src.api.main:app --reload</p>
                  </div>
                </div>
              </div>
            )}

            {/* Health Tab */}
            {tab === 'health' && (
              <div>
                <div className="card">
                  <div className="card-title" style={{ marginBottom: 16 }}>System Health</div>
                  {health ? (
                    <div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        padding: '14px 18px',
                        borderRadius: 10,
                        background: 'var(--risk-low-bg)',
                        marginBottom: 16,
                      }}>
                        <span style={{ fontSize: '1.5rem' }}>✓</span>
                        <div>
                          <div style={{ fontWeight: 700, color: 'var(--risk-low)' }}>
                            API Server Online
                          </div>
                          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {health.timestamp ? new Date(health.timestamp).toLocaleString() : ''}
                          </div>
                        </div>
                      </div>

                      <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                        <strong>Models loaded:</strong>{' '}
                        {health.models_loaded?.length > 0
                          ? health.models_loaded.join(', ')
                          : 'None — run training pipeline first'}
                      </div>
                    </div>
                  ) : (
                    <div className="error-message">Could not reach API server.</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
