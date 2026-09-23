import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMapEvents,
} from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

function PickHandler({ active, pickMode }) {
  useMapEvents({
    click(event) {
      if (active && pickMode) {
        active({ lat: event.latlng.lat, lng: event.latlng.lng, mode: pickMode })
      }
    },
  })
  return null
}

/**
 * Live map for a room.
 *  - members: sharing members [{ user, latitude, longitude, distanceLabel? }]
 *  - markers / events: arrays from the room snapshot (reacted to in real time)
 *  - pickMode + onPick activate click-to-place for markers/events.
 */
export function MapView({
  center,
  zoom = 14,
  myPosition,
  members = [],
  markers = [],
  events = [],
  pickMode = null,
  onPick = null,
}) {
  const hasCenter = Array.isArray(center) && typeof center[0] === 'number'

  if (!hasCenter) {
    return (
      <div className="map-placeholder">
        <p>No map center available.</p>
        <p className="muted">Share your location or open the room with other members to see them here.</p>
      </div>
    )
  }

  return (
    <MapContainer center={center} zoom={zoom} className="map-container">
      <TileLayer
        attribution='&amp;copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <PickHandler active={onPick} pickMode={pickMode} />

      {myPosition ? (
        <CircleMarker
          center={[myPosition.latitude, myPosition.longitude]}
          radius={10}
          pathOptions={{ color: '#1d4ed8', fillColor: '#3b82f6', fillOpacity: 0.95 }}
        >
          <Popup>You are here</Popup>
        </CircleMarker>
      ) : null}

      {members.map((m) => (
        <CircleMarker
          key={m.user.user_id}
          center={[m.latitude, m.longitude]}
          radius={8}
          pathOptions={{ color: '#047857', fillColor: '#10b981', fillOpacity: 0.8 }}
        >
          <Popup>
            <strong>{m.user.username}</strong>
            {m.distanceLabel ? <span> - {m.distanceLabel}</span> : null}
          </Popup>
        </CircleMarker>
      ))}

      {markers.map((m) => (
        <CircleMarker
          key={`marker-${m.id}`}
          center={[m.latitude, m.longitude]}
          radius={6}
          pathOptions={{ color: '#b45309', fillColor: '#f59e0b', fillOpacity: 0.9 }}
        >
          <Popup>
            <strong>{m.title}</strong>
            <br />
            {m.marker_type} by {m.created_by?.username}
          </Popup>
        </CircleMarker>
      ))}

      {events.map((e) => (
        <Circle
          key={`event-${e.id}`}
          center={[e.latitude, e.longitude]}
          radius={150}
          pathOptions={{ color: '#b91c1c', fillColor: '#ef4444', fillOpacity: 0.12 }}
        >
          <Popup>
            <strong>{e.title}</strong>
            <br />
            {e.description}
            <br />
            by {e.created_by?.username}
          </Popup>
        </Circle>
      ))}
    </MapContainer>
  )
}