export function formatTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function formatDateTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function formatRelative(iso) {
  if (!iso) return ''
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 45) return 'just now'
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`
  return `${Math.round(seconds / 86400)}d ago`
}

export function formatDistance(meters) {
  if (meters == null) return ''
  if (meters < 1000) return `${Math.round(meters)}m away`
  return `${(meters / 1000).toFixed(1)}km away`
}