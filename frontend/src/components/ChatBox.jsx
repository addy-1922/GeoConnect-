import { useEffect, useRef, useState } from 'react'

import { formatTime } from '../utils/format'

export function ChatBox({ messages = [], onSend, disabled = false }) {
  const [text, setText] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const submit = (event) => {
    event.preventDefault()
    const content = text.trim()
    if (!content || disabled) return
    onSend(content)
    setText('')
  }

  return (
    <div className="chatbox">
      <div className="chatbox-title">Room chat</div>
      <div className="chatbox-list">
        {messages.length === 0 ? <div className="chat-empty muted">No messages yet. Say hello!</div> : null}
        {messages.map((m) => (
          <div key={m.id} className={`chat-msg${m.sender_id === m.myId ? ' mine' : ''}`}>
            <div className="chat-head">
              <span className="chat-author">{m.sender?.username || m.sender_id}</span>
              <span className="chat-time muted">{formatTime(m.created_at)}</span>
            </div>
            <div className="chat-content">{m.content}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form className="chatbox-form" onSubmit={submit}>
        <input
          type="text"
          value={text}
          disabled={disabled}
          placeholder={disabled ? 'Connecting…' : 'Type a message…'}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit" disabled={disabled || !text.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}