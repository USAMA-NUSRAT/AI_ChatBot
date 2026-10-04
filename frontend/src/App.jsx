import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const history = [...messages, { role: 'user', content: text }]
    setMessages(history)
    setInput('')
    setError('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Only send role + content to the API
        body: JSON.stringify({
          messages: history.map(({ role, content }) => ({ role, content })),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      setMessages([...history, { role: 'assistant', content: data.reply, provider: data.provider }])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat">
      <header className="chat-header">
        <h1>Chatbot</h1>
        <button onClick={() => { setMessages([]); setError('') }} disabled={loading}>
          New chat
        </button>
      </header>

      <main className="chat-messages">
        {messages.length === 0 && <p className="empty">Say hello to start the conversation.</p>}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <div className="bubble">{m.content}</div>
            {m.provider && <span className="provider">via {m.provider}</span>}
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble typing">Thinking…</div>
          </div>
        )}
        {error && <div className="error">⚠ {error}</div>}
        <div ref={bottomRef} />
      </main>

      <form className="chat-input" onSubmit={sendMessage}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) sendMessage(e)
          }}
          placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
          rows={1}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

export default App
