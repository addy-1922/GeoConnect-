/**
 * WebSocket client helpers for GeoConnect.
 *
 * Connections are made to the Vite dev server (same origin), which proxies
 * `/ws` to Django Channels, so the session cookie authenticates the socket.
 */

export function connectWebSocket(path, handlers = {}, options = {}) {
  const { reconnectDelay = 2000, maxReconnect = 8 } = options
  const base = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  const url = `${base}${path}`

  let socket = null
  let closedByUser = false
  let attempts = 0
  let reconnectTimer = null

  const { onMessage = () => {}, onStatus = () => {}, onError = () => {} } = handlers

  function connect() {
    if (closedByUser) return
    onStatus(attempts === 0 ? 'connecting' : 'reconnecting')
    socket = new WebSocket(url)

    socket.onopen = () => {
      attempts = 0
      onStatus('open')
    }

    socket.onmessage = (event) => {
      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        data = { type: 'raw', text: event.data }
      }
      onMessage(data)
    }

    socket.onerror = (event) => onError(event)

    socket.onclose = () => {
      onStatus('closed')
      if (!closedByUser && attempts < maxReconnect) {
        attempts += 1
        reconnectTimer = setTimeout(connect, reconnectDelay * attempts)
      }
    }
  }

  connect()

  return {
    send(payload) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(payload))
        return true
      }
      return false
    },
    get readyState() {
      return socket ? socket.readyState : WebSocket.CLOSED
    },
    close() {
      closedByUser = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (socket) socket.close()
    },
  }
}