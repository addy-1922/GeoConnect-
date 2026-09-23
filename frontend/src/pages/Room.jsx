import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { ChatBox } from '../components/ChatBox'
import { LocationControls } from '../components/LocationControls'
import { MapView } from '../components/MapView'
import { MembersList } from '../components/MembersList'
import { useAuth } from '../context/AuthContext'
import { useGeolocation } from '../hooks/useGeolocation'
import * as api from '../services/api'
import { connectWebSocket } from '../services/websocket'
import { formatDistance } from '../utils/format'

const MARKER_TYPES = ['meeting_point', 'danger', 'food', 'parking', 'important', 'custom']

function upsertById(list, item) {
  const index = list.findIndex((x) => x.id === item.id)
  if (index === -1) return [...list, item]
  const next = [...list]
  next[index] = item
  return next
}

export function Room() {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [room, setRoom] = useState(null)
  const [myRole, setMyRole] = useState(null)
  const [participants, setParticipants] = useState([])
  const [onlineIds, setOnlineIds] = useState([])
  const [messages, setMessages] = useState([])
  const [locations, setLocations] = useState({})
  const [events, setEvents] = useState([])
  const [markers, setMarkers] = useState([])

  const [wsStatus, setWsStatus] = useState('connecting')
  const [sharing, setSharing] = useState(false)
  const [error, setError] = useState(null)
  const [picker, setPicker] = useState(null)
  const [note, setNote] = useState(null)

  const roomSocketRef = useRef(null)
  const locationSocketRef = useRef(null)

  const geo = useGeolocation({ intervalMs: 3000 })
  const wantShareRef = useRef(false)
  const [sharingRequested, setSharingRequested] = useState(false)

  // ------------------------------------------------------------------
  // Room (hub) socket
  // ------------------------------------------------------------------
  const handleRoomMessage = useCallback(
    (message) => {
      switch (message.type) {
        case 'room_snapshot':
          setRoom(message.room)
          setMyRole(message.my_role)
          setParticipants(message.participants || [])
          setOnlineIds(message.online_ids || [])
          setMessages(message.messages || [])
          setLocations(message.locations || {})
          setEvents(message.events || [])
          setMarkers(message.markers || [])
          break
        case 'user_joined':
          setParticipants((prev) => {
            if (prev.some((p) => p.user_id === message.user.user_id)) return prev
            return [...prev, message.user]
          })
          break
        case 'user_left':
          setParticipants((prev) => prev.filter((p) => p.user_id !== message.user.user_id))
          setLocations((prev) => {
            const next = { ...prev }
            delete next[String(message.user.user_id)]
            return next
          })
          setOnlineIds((prev) => prev.filter((id) => id !== message.user.user_id))
          break
        case 'presence':
          setOnlineIds(message.online_ids || [])
          break
        case 'chat_message':
          setMessages((prev) => upsertById(prev, message.message))
          break
        case 'event_created':
          setEvents((prev) => upsertById(prev, message.event))
          setNote(`${message.event.created_by?.username || 'Someone'} created event '${message.event.title}'`)
          break
        case 'marker_created':
          setMarkers((prev) => upsertById(prev, message.marker))
          setNote(`${message.marker.created_by?.username || 'Someone'} added marker '${message.marker.title}'`)
          break
        case 'error':
          setError(message.message)
          break
        default:
          break
      }
    },
    [],
  )

  useEffect(() => {
    if (!user) return undefined
    const socket = connectWebSocket(`/ws/rooms/${roomId}/`, {
      onStatus: setWsStatus,
      onMessage: handleRoomMessage,
    })
    roomSocketRef.current = socket
    return () => socket.close()
  }, [roomId, user, handleRoomMessage])

  // ------------------------------------------------------------------
  // Location socket
  // ------------------------------------------------------------------
  const handleLocationMessage = useCallback(
    (message) => {
      if (message.type === 'location_update' || message.type === 'location_shared') {
        setLocations((prev) => ({
          ...prev,
          [String(message.user.user_id)]: {
            latitude: message.latitude,
            longitude: message.longitude,
            accuracy: message.accuracy,
            updated_at: message.updated_at,
          },
        }))
        if (message.user.user_id === user?.user_id) setSharing(true)
      } else if (message.type === 'location_stopped') {
        setLocations((prev) => {
          const next = { ...prev }
          delete next[String(message.user.user_id)]
          return next
        })
        if (message.user.user_id === user?.user_id) setSharing(false)
      }
    },
    [user],
  )

  useEffect(() => {
    if (!user) return undefined
    const socket = connectWebSocket(`/ws/location/${roomId}/`, {
      onStatus: () => {},
      onMessage: handleLocationMessage,
    })
    locationSocketRef.current = socket
    return () => socket.close()
  }, [roomId, user, handleLocationMessage])

  // Push each fresh geolocation fix while sharing is requested.
  useEffect(() => {
    if (!sharingRequested) return
    if (!geo.position) return
    const socket = locationSocketRef.current
    if (!socket || !socket.send({ type: 'location_update', ...geo.position })) return
    setSharing(true)
  }, [geo.position, sharingRequested])

  const startSharing = useCallback(() => {
    setError(null)
    setSharingRequested(true)
    wantShareRef.current = true
    if (geo.status !== 'active') geo.start()
  }, [geo])

  const stopSharing = useCallback(() => {
    setSharingRequested(false)
    wantShareRef.current = false
    geo.stop()
    locationSocketRef.current?.send({ type: 'stop_sharing' })
    setSharing(false)
  }, [geo])

  // ------------------------------------------------------------------
  // Members management (REST)
  // ------------------------------------------------------------------
  const refreshMembers = useCallback(async () => {
    try {
      const members = await api.listMembers(roomId)
      setParticipants(members)
    } catch (err) {
      setError(err.message)
    }
  }, [roomId])

  const runMutation = useCallback(
    async (fn) => {
      setError(null)
      try {
        await fn()
        await refreshMembers()
      } catch (err) {
        setError(err.message)
      }
    },
    [refreshMembers],
  )

  const addMember = useCallback(
    (username) => runMutation(() => api.addMember(roomId, { username })),
    [runMutation, roomId],
  )

  const changeRole = useCallback(
    (userId, role) => runMutation(() => api.updateMemberRole(roomId, userId, role)),
    [runMutation, roomId],
  )

  const removeMember = useCallback(
    (userId) => runMutation(() => api.removeMember(roomId, userId)),
    [runMutation, roomId],
  )

  const leave = useCallback(async () => {
    setError(null)
    try {
      await api.leaveRoom(roomId)
      navigate('/')
    } catch (err) {
      setError(err.message)
    }
  }, [roomId, navigate])

  const deleteRoom = useCallback(async () => {
    setError(null)
    if (!window.confirm('Delete this room for everyone? This cannot be undone.')) return
    try {
      await api.deleteRoom(roomId)
      navigate('/')
    } catch (err) {
      setError(err.message)
    }
  }, [roomId, navigate])

  // ------------------------------------------------------------------
  // Chat / events / markers via the hub socket
  // ------------------------------------------------------------------
  const sendChat = useCallback((content) => {
    roomSocketRef.current?.send({ type: 'chat_message', content })
  }, [])

  const pickEvent = useCallback(() => {
    setError(null)
    setNote('Click anywhere on the map to place the event.')
    setPicker({ mode: 'event', lat: null, lng: null })
  }, [])

  const pickMarker = useCallback(() => {
    setError(null)
    setNote('Click anywhere on the map to place the marker.')
    setPicker({ mode: 'marker', lat: null, lng: null })
  }, [])

  const handlePick = useCallback(({ lat, lng, mode }) => {
    setPicker({ mode, lat, lng })
  }, [])

  const cancelPick = useCallback(() => {
    setPicker(null)
    setNote(null)
  }, [])

  const submitEvent = useCallback(
    async (payload) => {
      roomSocketRef.current?.send({ type: 'event_created', ...payload })
      setPicker(null)
      setNote(null)
    },
    [],
  )

  const submitMarker = useCallback(
    async (payload) => {
      roomSocketRef.current?.send({ type: 'marker_created', ...payload })
      setPicker(null)
      setNote(null)
    },
    [],
  )

  // ------------------------------------------------------------------
  // Derived data
  // ------------------------------------------------------------------
  const myUserId = user?.user_id

  const membersWithDistance = useMemo(() => {
    if (!myUserId) return []
    return Object.entries(locations)
      .filter(([id]) => Number(id) !== myUserId)
      .map(([id, loc]) => {
        const participant = participants.find((p) => String(p.user_id) === id)
        let distanceLabel
        if (geo.position) {
          distanceLabel = formatDistance(haversine(geo.position, loc))
        }
        return { user: participant || { user_id: Number(id), username: `user ${id}` }, ...loc, distanceLabel }
      })
  }, [locations, participants, myUserId, geo.position])

  const mapCenter = useMemo(() => {
    if (geo.position) return [geo.position.latitude, geo.position.longitude]
    const first = Object.values(locations)[0]
    if (first) return [first.latitude, first.longitude]
    return null
  }, [geo.position, locations])

  if (room && wsStatus === 'closed') {
    return (
      <div className="card room-error">
        <p>The room connection was lost.</p>
      </div>
    )
  }

  return (
    <div className="room-page">
      <div className="room-head">
        <div>
          <h1>{room?.name || 'Loading…'}</h1>
          <span className="muted">
            {room?.is_private ? 'Private room' : 'Public room'}
            {myRole ? <span className="badge">you: {myRole}</span> : null}
          </span>
        </div>
        <div className="room-actions">
          {myRole === 'OWNER' || myRole === 'ADMIN' ? (
            <button type="button" className="secondary-btn" onClick={pickEvent}>
              Add event
            </button>
          ) : null}
          {myRole === 'OWNER' || myRole === 'ADMIN' ? (
            <button type="button" className="secondary-btn" onClick={pickMarker}>
              Add marker
            </button>
          ) : null}
          {myRole && myRole !== 'OWNER' ? (
            <button type="button" className="secondary-btn" onClick={leave}>
              Leave room
            </button>
          ) : null}
          {myRole === 'OWNER' ? (
            <button type="button" className="danger-btn" onClick={deleteRoom}>
              Delete room
            </button>
          ) : null}
        </div>
      </div>

      {note ? <div className="note">{note}</div> : null}
      {error ? <div className="form-error">{error}</div> : null}

      <div className="room-grid">
        <div className="room-map-col">
          <MapView
            center={mapCenter}
            myPosition={geo.position}
            members={membersWithDistance}
            markers={markers}
            events={events}
            pickMode={picker?.mode || null}
            onPick={picker ? handlePick : null}
          />

          {picker ? (
            picker.lat == null ? (
              <div className="picker-wait">Click the map to place the {picker.mode === 'event' ? 'event' : 'marker'}…</div>
            ) : (
              <CreatePointPanel
                mode={picker.mode}
                lat={picker.lat}
                lng={picker.lng}
                onSubmit={picker.mode === 'event' ? submitEvent : submitMarker}
                onCancel={cancelPick}
              />
            )
          ) : (
            <LocationControls
              sharing={sharing}
              position={geo.position}
              status={geo.status}
              error={geo.error}
              onStart={startSharing}
              onStop={stopSharing}
            />
          )}

          <div className="room-side">
            <MembersList
              participants={participants}
              onlineIds={onlineIds}
              myUserId={myUserId}
              myRole={myRole}
              onRoleChange={changeRole}
              onRemove={removeMember}
              onAddMember={addMember}
            />
          </div>
        </div>

        <div className="room-right">
          <ChatBox messages={messages} onSend={sendChat} disabled={wsStatus !== 'open'} />
        </div>
      </div>
    </div>
  )
}

function haversine(a, b) {
  const R = 6371000
  const toRad = (x) => (x * Math.PI) / 180
  const dLat = toRad(b.latitude - a.latitude)
  const dLng = toRad(b.longitude - a.longitude)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}

function CreatePointPanel({ mode, lat, lng, onSubmit, onCancel }) {
  const [title, setTitle] = useState('')
  const [type, setType] = useState('POINT')
  const [description, setDescription] = useState('')
  const [startTime, setStartTime] = useState('')

  const isEvent = mode === 'event'

  const submit = (event) => {
    event.preventDefault()
    onSubmit({
      title,
      ...(isEvent
        ? { description, start_time: startTime ? new Date(startTime).toISOString() : null }
        : { marker_type: type }),
      latitude: lat,
      longitude: lng,
    })
  }

  return (
    <form className="create-panel card" onSubmit={submit}>
      <strong>Place {isEvent ? 'event' : 'marker'}</strong>
      <div className="muted">at {lat.toFixed(5)}, {lng.toFixed(5)}</div>
      <label>
        Title
        <input type="text" value={title} onChange={(event) => setTitle(event.target.value)} required />
      </label>
      {isEvent ? (
        <>
          <label>
            Description
            <textarea rows={2} value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label>
            Start time
            <input
              type="datetime-local"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
            />
          </label>
        </>
      ) : (
        <label>
          Type
          <select value={type} onChange={(event) => setType(event.target.value)}>
            {MARKER_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="btn-row">
        <button className="primary-btn" type="submit" disabled={!title.trim()}>
          Create
        </button>
        <button className="secondary-btn" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  )
}