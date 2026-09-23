import { useEffect, useRef, useState } from 'react'

import { useNotifications } from '../context/NotificationsContext'
import { formatRelative } from '../utils/format'

export function NotificationsBell() {
  const { items, unread, markRead, markAllRead } = useNotifications()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    function onClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  return (
    <div className="notif-wrap" ref={menuRef}>
      <button
        className="nav-link notif-bell"
        type="button"
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
      >
        Bell{unread > 0 ? <span className="notif-badge">{unread}</span> : null}
      </button>
      {open ? (
        <div className="notif-menu">
          <div className="notif-menu-head">
            <strong>Notifications</strong>
            <button type="button" className="text-btn" onClick={markAllRead} disabled={unread === 0}>
              Mark all read
            </button>
          </div>
          <div className="notif-list">
            {items.length === 0 ? <div className="notif-empty">No notifications yet.</div> : null}
            {items.map((n) => (
              <button
                key={n.id}
                type="button"
                className={`notif-item${n.is_read ? '' : ' unread'}`}
                onClick={() => markRead(n.id)}
              >
                <span className="notif-msg">{n.message}</span>
                <span className="notif-time">{formatRelative(n.created_at)}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}