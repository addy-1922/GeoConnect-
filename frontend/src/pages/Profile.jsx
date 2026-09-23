import { useState } from 'react'

import { useAuth } from '../context/AuthContext'
import * as api from '../services/api'

const STATUSES = [
  { value: 'online', label: 'Online' },
  { value: 'away', label: 'Away' },
  { value: 'offline', label: 'Offline' },
]

export function Profile() {
  const { user, refreshMe } = useAuth()
  const [status, setStatus] = useState(user?.status || 'offline')
  const [file, setFile] = useState(null)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const apply = async (event) => {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setBusy(true)
    try {
      const formData = new FormData()
      formData.set('status', status)
      if (file) formData.set('avatar', file)
      const updated = await api.updateMe(formData)
      await refreshMe()
      setFile(null)
      setMessage(`Saved at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`)
      setStatus(updated.status)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="profile-page">
      <section className="card">
        <h1>Profile</h1>

        <div className="avatar-row">
          {user?.avatar ? <img className="avatar-img" src={user.avatar} alt="avatar" /> : (
            <div className="avatar-img avatar-placeholder">{user?.username?.[0]?.toUpperCase()}</div>
          )}
          <div>
            <strong>{user?.username}</strong>
            <div className="muted">{user?.email}</div>
            <div className="muted">Last seen: {user?.last_seen ? new Date(user.last_seen).toLocaleString() : 'never'}</div>
            <div className="muted">
              Sharing location: {user?.is_sharing_location ? 'yes' : 'no'}
            </div>
          </div>
        </div>

        <form onSubmit={apply}>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Avatar
            <input type="file" accept="image/*" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          </label>

          {message ? <div className="form-success">{message}</div> : null}
          {error ? <div className="form-error">{error}</div> : null}

          <button className="primary-btn" type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save profile'}
          </button>
        </form>
      </section>
    </div>
  )
}