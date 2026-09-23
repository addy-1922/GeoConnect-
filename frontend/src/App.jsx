import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { Navbar } from './components/Navbar'
import { AuthProvider, useAuth } from './context/AuthContext'
import { NotificationsProvider } from './context/NotificationsContext'
import { Dashboard } from './pages/Dashboard'
import { Login } from './pages/Login'
import { Profile } from './pages/Profile'
import { Register } from './pages/Register'
import { Room } from './pages/Room'

function Protected() {
  const { user, loading } = useAuth()
  if (loading) return <div className="app-loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return (
    <>
      <Navbar />
      <main className="app-main">
        <Outlet />
      </main>
    </>
  )
}

function PublicOnly() {
  const { user, loading } = useAuth()
  if (loading) return <div className="app-loading">Loading…</div>
  if (user) return <Navigate to="/" replace />
  return <Outlet />
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationsProvider>
          <Routes>
            <Route element={<PublicOnly />}>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Route>
            <Route element={<Protected />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/rooms/:roomId" element={<Room />} />
              <Route path="/profile" element={<Profile />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </NotificationsProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App