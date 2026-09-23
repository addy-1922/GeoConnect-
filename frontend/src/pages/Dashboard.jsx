import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import * as api from '../services/api'

export function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [rooms, setRooms] = useState([])
  const [loading, setLoading] = useState(true)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [creating, setCreating] = useState(false)

  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)

  const [error, setError] = useState(null)

  const loadRooms = useCallback(async () => {
    try {
      setRooms(await api.listRooms())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRooms()
  }, [loadRooms])

  const create = async (event) => {
    event.preventDefault()
    setError(null)
    setCreating(true)
    try {
      const room = await api.createRoom({ name, description, is_private: isPrivate })
      navigate(`/rooms/${room.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const search = async (event) => {
    event.preventDefault()
    setError(null)
    if (!query.trim()) return
    setSearching(true)
    try {
      setResults(await api.searchAll(query))
    } catch (err) {
      setError(err.message)
    } finally {
      setSearching(false)
    }
  }

  const openOrJoin = async (room, exists) => {
    setError(null)
    try {
      if (!exists) {
        await api.joinRoom(room.id)
      }
      navigate(`/rooms/${room.id}`)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="dashboard">
      <section className="dash-hero">
        <h1>Hi, {user?.username}</h1>
        <p className="muted">Create a room, invite people, and share live locations, markers and events.</p>
      </section>

      {error ? <div className="form-error">{error}</div> : null}

      <div className="dash-cols">
        <section className="card">
          <h2>New room</h2>
          <form onSubmit={create}>
            <label>
              Room name
              <input type="text" value={name} onChange={(event) => setName(event.target.value)} required />
            </label>
            <label>
              Description
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={2}
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={isPrivate}
                onChange={(event) => setIsPrivate(event.target.checked)}
              />
              Private room (join by invite only)
            </label>
            <button className="primary-btn" type="submit" disabled={creating || !name.trim()}>
              {creating ? 'Creating…' : 'Create room'}
            </button>
          </form>
        </section>

        <section className="card">
          <h2>Find a room</h2>
          <form onSubmit={search}>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by room name…"
            />
            <button className="primary-btn" type="submit" disabled={searching || !query.trim()}>
              {searching ? 'Searching…' : 'Search'}
            </button>
          </form>

          {results.length > 0 ? (
            <ul className="room-list">
              {results.map((room) => {
                const exists = Boolean(room.my_role)
                return (
                  <li key={room.id} className="room-row">
                    <div className="room-info">
                      <strong>{room.name}</strong>
                      <span className="muted">
                        {room.description || 'No description'}
                        {room.is_private ? ' - private' : ''} - {room.member_count} member(s)
                      </span>
                    </div>
                    <button
                      type="button"
                      className="primary-btn"
                      onClick={() => openOrJoin(room, exists)}
                    >
                      {exists ? 'Open' : 'Join'}
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : null}
        </section>
      </div>

      <section className="card">
        <h2>Your rooms</h2>
        {loading ? <p className="muted">Loading…</p> : null}
        {!loading && rooms.length === 0 ? <p className="muted">You have no rooms yet.</p> : null}
        <ul className="room-list">
          {rooms.map((room) => (
            <li key={room.id} className="room-row">
              <div className="room-info">
                <strong>{room.name}</strong>
                <span className="muted">
                  {room.description || 'No description'}
                  {room.is_private ? ' - private' : ''} - {room.member_count} member(s)
                </span>
              </div>
              <div className="room-meta">
                {room.my_role ? <span className="badge">{room.my_role}</span> : null}
                <button type="button" className="secondary-btn" onClick={() => navigate(`/rooms/${room.id}`)}>
                  Open
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}