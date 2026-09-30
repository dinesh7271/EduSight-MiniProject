import { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // Synchronous initialization from localStorage prevents race condition redirects on mount
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('edusight_token') || null
    } catch {
      return null
    }
  })

  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('edusight_user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  const [role, setRole] = useState(() => {
    try {
      const saved = localStorage.getItem('edusight_user')
      if (saved) {
        const parsed = JSON.parse(saved)
        return parsed?.role || null
      }
      return null
    } catch {
      return null
    }
  })

  const login = (tokenValue, userData) => {
    setToken(tokenValue)
    setUser(userData)
    setRole(userData?.role || null)
    try {
      localStorage.setItem('edusight_token', tokenValue)
      localStorage.setItem('edusight_user', JSON.stringify(userData))
    } catch (e) {
      console.warn('Could not persist to localStorage:', e)
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    setRole(null)
    try {
      localStorage.removeItem('edusight_token')
      localStorage.removeItem('edusight_user')
    } catch (e) {
      console.warn('Could not clear localStorage:', e)
    }
  }

  const isAuthenticated = Boolean(token)

  return (
    <AuthContext.Provider value={{ user, token, role, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
