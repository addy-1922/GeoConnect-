/**
 * API client for the GeoConnect backend.
 *
 * Auth model: session cookie + CSRF token (cosigned by Django).
 *  - All requests go through the Vite proxy, so they are same-origin to the
 *    browser and the session cookie is sent automatically.
 *  - State-changing requests carry `X-CSRFToken`. On a CSRF rejection the
 *    token is re-fetched and the request retried once.
 */

export const API_BASE_URL = '/api'

function readCsrfCookie() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

let csrfToken = readCsrfCookie()

export async function fetchCsrf() {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: 'same-origin' })
  if (!response.ok) throw new Error('Could not obtain CSRF token.')
  const data = await response.json()
  csrfToken = data.csrfToken || readCsrfCookie()
  return csrfToken
}

async function request(path, options = {}) {
  const { method = 'GET', body, headers = {}, retried = false } = options

  const unsafe = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())
  if (unsafe && !csrfToken) {
    await fetchCsrf()
  }

  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  const fetchOptions = {
    method,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(body !== undefined && !isForm ? { 'Content-Type': 'application/json' } : {}),
      ...(unsafe ? { 'X-CSRFToken': csrfToken } : {}),
      ...headers,
    },
    ...(body !== undefined
      ? { body: isForm ? body : typeof body === 'string' ? body : JSON.stringify(body) }
      : {}),
  }

  const response = await fetch(`${API_BASE_URL}${path}`, fetchOptions)

  if (!response.ok) {
    if (response.status === 403 && unsafe && !retried) {
      await fetchCsrf()
      return request(path, { ...options, retried: true })
    }
    let detail = `Request failed: ${response.status} ${response.statusText}`
    try {
      const data = await response.json()
      if (data.detail) detail = typeof data.detail === 'string' ? data.detail : detail
      if (data.detail && typeof data.detail !== 'string') detail = `${detail}: ${JSON.stringify(data.detail)}`
    } catch {
      /* keep default message */
    }
    const error = new Error(detail)
    error.status = response.status
    throw error
  }

  if (response.status === 204) return null
  return response.json()
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------
async function applyAuthResult(data) {
  csrfToken = data.csrfToken || readCsrfCookie() || csrfToken
  return data.user
}

export function login(payload) {
  return request('/auth/login/', { method: 'POST', body: payload }).then(applyAuthResult)
}

export function register(payload) {
  return request('/auth/register/', { method: 'POST', body: payload }).then(applyAuthResult)
}

export function logout() {
  return request('/auth/logout/', { method: 'POST' })
}

export function me() {
  return request('/users/me/')
}

export function updateMe(payload) {
  return request('/users/me/', { method: 'PATCH', body: payload })
}

export function searchUsers(query) {
  return request(`/users/?search=${encodeURIComponent(query || '')}`)
}

// ---------------------------------------------------------------------------
// Rooms
// ---------------------------------------------------------------------------
export function listRooms() {
  return request('/rooms/')
}

export function createRoom(payload) {
  return request('/rooms/', { method: 'POST', body: payload })
}

export function getRoom(roomId) {
  return request(`/rooms/${roomId}/`)
}

export function joinRoom(roomId) {
  return request(`/rooms/${roomId}/join/`, { method: 'POST' })
}

export function leaveRoom(roomId) {
  return request(`/rooms/${roomId}/leave/`, { method: 'POST' })
}

export function updateRoom(roomId, payload) {
  return request(`/rooms/${roomId}/`, { method: 'PATCH', body: payload })
}

export function deleteRoom(roomId) {
  return request(`/rooms/${roomId}/`, { method: 'DELETE' })
}

export function listMembers(roomId) {
  return request(`/rooms/${roomId}/members/`)
}

export function addMember(roomId, payload) {
  return request(`/rooms/${roomId}/members/`, { method: 'POST', body: payload })
}

export function updateMemberRole(roomId, userId, role) {
  return request(`/rooms/${roomId}/members/${userId}/`, { method: 'PATCH', body: { role } })
}

export function removeMember(roomId, userId) {
  return request(`/rooms/${roomId}/members/${userId}/`, { method: 'DELETE' })
}

export function searchAll(query) {
  return request(`/rooms/search/?q=${encodeURIComponent(query || '')}`)
}

// ---------------------------------------------------------------------------
// Messages / locations / events / markers (REST fallbacks)
// ---------------------------------------------------------------------------
export function listMessages(roomId, before) {
  const suffix = before ? `?before=${before}` : ''
  return request(`/rooms/${roomId}/messages/${suffix}`)
}

export function sendMessage(roomId, content) {
  return request(`/rooms/${roomId}/messages/`, { method: 'POST', body: { content } })
}

export function listLocations(roomId) {
  return request(`/rooms/${roomId}/locations/`)
}

export function listNearby(roomId) {
  return request(`/rooms/${roomId}/nearby/`)
}

export function listEvents(roomId) {
  return request(`/rooms/${roomId}/events/`)
}

export function createEvent(roomId, payload) {
  return request(`/rooms/${roomId}/events/`, { method: 'POST', body: payload })
}

export function listMarkers(roomId) {
  return request(`/rooms/${roomId}/markers/`)
}

export function createMarker(roomId, payload) {
  return request(`/rooms/${roomId}/markers/`, { method: 'POST', body: payload })
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------
export function listNotifications() {
  return request('/notifications/')
}

export function unreadCount() {
  return request('/notifications/unread-count/')
}

export function markNotificationRead(notificationId) {
  return request(`/notifications/${notificationId}/read/`, { method: 'POST' })
}

export function markAllNotificationsRead() {
  return request('/notifications/mark-all-read/', { method: 'POST' })
}

export { request as rawRequest }