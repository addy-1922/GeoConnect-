import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '', password_confirm: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const setField = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>Create account</h1>
        <p className="muted">Join GeoConnect and start a room.</p>

        <label>
          Username
          <input type="text" value={form.username} onChange={setField('username')} autoComplete="username" required />
        </label>

        <label>
          Email
          <input type="email" value={form.email} onChange={setField('email')} autoComplete="email" required />
        </label>

        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={setField('password')}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>

        <label>
          Confirm password
          <input
            type="password"
            value={form.password_confirm}
            onChange={setField('password_confirm')}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </label>

        {error ? <div className="form-error">{error}</div> : null}

        <button className="primary-btn" type="submit" disabled={busy}>
          {busy ? 'Creating…' : 'Sign up'}
        </button>

        <p className="muted">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  )
}