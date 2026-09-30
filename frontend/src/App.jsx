import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import LoginPage        from './pages/LoginPage.jsx';
import StudentDashboard from './pages/StudentDashboard.jsx';
import FacultyDashboard from './pages/FacultyDashboard.jsx';
import AdminPanel       from './pages/AdminPanel.jsx';

// ── Role-to-default-path mapping ─────────────────────────────────
const ROLE_HOME = {
  STUDENT: '/dashboard',
  FACULTY: '/faculty',
  TEACHER: '/faculty',
  ADMIN:   '/admin',
};

// ── PrivateRoute ─────────────────────────────────────────────────
function PrivateRoute({ children, allowedRoles }) {
  const { isAuthenticated, role, token } = useAuth();
  const location = useLocation();

  const isAuthed = Boolean(isAuthenticated || token);

  if (!isAuthed) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const userRole = role?.toUpperCase();

  // Admin has access to all dashboards
  if (userRole === 'ADMIN') {
    return children;
  }

  if (allowedRoles && userRole && !allowedRoles.includes(userRole)) {
    const home = ROLE_HOME[userRole] || '/login';
    return <Navigate to={home} replace />;
  }

  return children;
}

// ── Root redirect ────────────────────────────────────────────────
function RootRedirect() {
  const { isAuthenticated, role, token } = useAuth();
  const isAuthed = Boolean(isAuthenticated || token);
  if (!isAuthed) return <Navigate to="/login" replace />;
  const home = ROLE_HOME[role?.toUpperCase()] || '/dashboard';
  return <Navigate to={home} replace />;
}

// ── App ──────────────────────────────────────────────────────────
export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Root → smart redirect based on login status and role */}
      <Route path="/" element={<RootRedirect />} />

      {/* Student Dashboard */}
      <Route
        path="/dashboard"
        element={
          <PrivateRoute allowedRoles={['STUDENT', 'ADMIN']}>
            <StudentDashboard />
          </PrivateRoute>
        }
      />

      {/* Faculty Dashboard */}
      <Route
        path="/faculty"
        element={
          <PrivateRoute allowedRoles={['FACULTY', 'TEACHER', 'ADMIN']}>
            <FacultyDashboard />
          </PrivateRoute>
        }
      />

      {/* Admin Panel */}
      <Route
        path="/admin"
        element={
          <PrivateRoute allowedRoles={['ADMIN']}>
            <AdminPanel />
          </PrivateRoute>
        }
      />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
