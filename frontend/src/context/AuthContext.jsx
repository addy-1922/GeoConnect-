import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import * as api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function bootstrap() {
      try {
        const me = await api.me()
        if (!cancelled) setUser(me)
      } catch {
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (payload) => {
    const me = await api.login(payload)
    setUser(me)
    return me
  }, [])

  const register = useCallback(async (payload) => {
    const me = await api.register(payload)
    setUser(me)
    return me
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      /* session may already be gone */
    }
    setUser(null)
  }, [])

  const refreshMe = useCallback(async () => {
    const me = await api.me()
    setUser(me)
    return me
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshMe }),
    [user, loading, login, register, logout, refreshMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (ctx === null) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}