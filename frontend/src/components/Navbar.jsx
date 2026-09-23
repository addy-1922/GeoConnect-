import { useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { NotificationsBell } from './NotificationsBell'

export function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <header className="navbar">
      <button className="brand" onClick={() => navigate('/')} type="button">
        GeoConnect
      </button>
      <nav className="nav-actions">
        <NotificationsBell />
        <button className="nav-link" onClick={() => navigate('/profile')} type="button">
          {user?.username || 'Profile'}
        </button>
        <button className="nav-link nav-logout" onClick={handleLogout} type="button">
          Log out
        </button>
      </nav>
    </header>
  )
}