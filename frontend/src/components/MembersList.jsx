import { useState } from 'react'

export function MembersList({
  participants = [],
  onlineIds = [],
  myUserId,
  myRole,
  onRoleChange,
  onRemove,
  onAddMember,
}) {
  const [username, setUsername] = useState('')
  const [expanded, setExpanded] = useState(false)

  const online = new Set(onlineIds)
  const canManage = myRole === 'OWNER' || myRole === 'ADMIN'

  const roles = ['OWNER', 'ADMIN', 'MEMBER']

  const submit = (event) => {
    event.preventDefault()
    const name = username.trim()
    if (!name) return
    onAddMember(name)
    setUsername('')
  }

  return (
    <div className="members">
      <div className="members-head" onClick={() => setExpanded((v) => !v)} role="button" tabIndex={0}>
        <span>Members ({participants.length})</span>
        <span className="muted">{expanded ? 'hide' : 'show'}</span>
      </div>

      {canManage && (
        <form className="members-add" onSubmit={submit}>
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="Add member by username"
          />
          <button type="submit">Add</button>
        </form>
      )}

      {expanded || myRole === 'OWNER' ? (
        <ul className="members-list">
          {participants.map((p) => {
            const isMe = p.user_id === myUserId
            const isOwner = p.role === 'OWNER'
            return (
              <li key={p.user_id} className="member-row">
                <span className={`member-dot${online.has(p.user_id) ? ' online' : ''}`} />
                <span className="member-name">
                  {p.username || p.user?.username || p.user_id}
                  {isMe ? <em> (you)</em> : null}
                </span>
                <span className="member-role">{p.role}</span>
                {canManage && !isMe && !isOwner ? (
                  <span className="member-actions">
                    <select
                      value={p.role}
                      onChange={(event) => onRoleChange(p.user_id, event.target.value)}
                      disabled={!canManage}
                    >
                      {roles.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                    <button type="button" className="danger-btn" onClick={() => onRemove(p.user_id)}>
                      Remove
                    </button>
                  </span>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}