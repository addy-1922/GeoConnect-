import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Wraps the browser Geolocation API.
 *   position: {latitude, longitude, accuracy} | null
 *   status: 'idle' | 'prompt' | 'active' | 'error'
 *   error:  message string | null
 *   start(): begin watching (optionally throttled by intervalMs).
 *   stop(): stop the watch, keep last position.
 */
export function useGeolocation({ intervalMs = 3000 } = {}) {
  const [position, setPosition] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const watchIdRef = useRef(null)
  const latestRef = useRef(null)

  const handlePosition = useCallback(
    (pos) => {
      const { latitude, longitude, accuracy } = pos.coords
      const now = Date.now()
      if (intervalMs > 0 && latestRef.current && now - latestRef.current < intervalMs) return
      latestRef.current = now
      setPosition({ latitude, longitude, accuracy })
      setError(null)
      setStatus('active')
    },
    [intervalMs],
  )

  const handleFailure = useCallback((err) => {
    setStatus('error')
    setError(err?.message || 'Could not obtain your location.')
  }, [])

  const start = useCallback(
    (options) => {
      if (!navigator.geolocation) {
        setStatus('error')
        setError('Geolocation is not supported by this browser.')
        return
      }
      setStatus('prompt')
      watchIdRef.current = navigator.geolocation.watchPosition(
        handlePosition,
        handleFailure,
        { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000, ...options },
      )
    },
    [handlePosition, handleFailure],
  )

  const stop = useCallback(() => {
    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current)
      watchIdRef.current = null
    }
    setStatus('idle')
  }, [])

  useEffect(() => () => stop(), [stop])

  return { position, status, error, start, stop }
}