import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import * as api from '../services/api'
import { connectWebSocket } from '../services/websocket'
import { useAuth } from './AuthContext'

const NotificationsContext = createContext(null)

export function NotificationsProvider({ children }) {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [unread, setUnread] = useState(0)
  const socketRef = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const list = await api.listNotifications()
      setItems(list)
      const count = await api.unreadCount()
      setUnread(count.count)
    } catch {
      /* offline - keep current state */
    }
  }, [])

  useEffect(() => {
    if (!user) {
      setItems([])
      setUnread(0)
      return undefined
    }
    refresh()

    const socket = connectWebSocket('/ws/notifications/', {
      onMessage: (message) => {
        if (message.type === 'notification') {
          setItems((prev) => [message, ...prev].slice(0, 100))
          setUnread((prev) => prev + 1)
        }
      },
    })
    socketRef.current = socket
    return () => {
      socket.close()
      socketRef.current = null
    }
  }, [user, refresh])

  const markRead = useCallback(async (id) => {
    try {
      await api.markNotificationRead(id)
    } catch {
      /* ignore */
    }
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    setUnread((prev) => Math.max(0, prev - (items.find((n) => n.id === id && !n.is_read) ? 1 : 0)))
  }, [items])

  const markAllRead = useCallback(async () => {
    try {
      await api.markAllNotificationsRead()
    } catch {
      /* ignore */
    }
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })))
    setUnread(0)
  }, [])

  const value = useMemo(
    () => ({ items, unread, refresh, markRead, markAllRead }),
    [items, unread, refresh, markRead, markAllRead],
  )

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext)
  if (ctx === null) throw new Error('useNotifications must be used within NotificationsProvider')
  return ctx
}