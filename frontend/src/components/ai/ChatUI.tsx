import { useState } from 'react'

export function ChatUI() {
  const [messages, setMessages] = useState<Array<{role: string; text: string}>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function send() {
    if (!input) return
    const userMsg = { role: 'user', text: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
      const res = await fetch('/api/ai', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ message: input }) })
      if (!res.ok) throw new Error('assistant error')
      const data = await res.json()
      const reply = data.reply || data.message || 'No response'
      setMessages(prev => [...prev, { role: 'assistant', text: reply }])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border rounded p-4">
      <div className="h-60 overflow-auto mb-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right mb-2' : 'text-left mb-2'}>
            <div className={`inline-block px-3 py-2 rounded ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-black'}`}>
              {m.text}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input className="input-field flex-1" value={input} onChange={e => setInput(e.target.value)} placeholder="Ask the assistant" />
        <button className="btn-primary" onClick={send} disabled={loading}>{loading ? '…' : 'Send'}</button>
      </div>
    </div>
  )
}
