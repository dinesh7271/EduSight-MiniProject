import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Graduation cap SVG icon
function GradCapIcon({ size = 24, color = '#fff' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3z" fill={color} />
      <path d="M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z" fill={color} opacity="0.8" />
    </svg>
  )
}

export default function NavBar({ userName, role, onLogout }) {
  const roleBadgeClass =
    role === 'ADMIN' ? 'badge-admin' :
    role === 'FACULTY' ? 'badge-faculty' :
    'badge-student'

  const roleLabel =
    role === 'ADMIN' ? 'Admin' :
    role === 'FACULTY' ? 'Faculty' :
    'Student'

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="navbar-brand">
          <div className="navbar-logo-icon">
            <GradCapIcon size={20} color="#fff" />
          </div>
          <span className="navbar-brand-name">EduSight</span>
        </Link>

        <div className="navbar-user">
          <span className={`badge ${roleBadgeClass}`}>{roleLabel}</span>
          <span className="navbar-username">{userName}</span>
          <button
            onClick={onLogout}
            className="btn btn-secondary btn-sm"
            style={{ marginLeft: 4 }}
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
