/**
 * Chat UI wired to backend AI assistant proxy (/api/ai/chat).
 * Keeps a local 10-turn window, mirrors server session history, and surfaces tool suggestions.
 */
'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { aiClient } from '@/lib/aiClient'

type Msg = { role: 'user' | 'assistant' | 'tool'; text: string }

export function ChatUI() {
  const [sessionId] = useState(() => uuidv4())
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load existing history (if any)
    aiClient
      .history(sessionId)
      .then((history) => {
        if (history?.length) setMessages(history.map((h) => ({ role: h.role as Msg['role'], text: h.content || h.text || '' })))
      })
      .catch(() => void 0)
  }, [sessionId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  async function send() {
    if (!input.trim()) return
    const userMsg: Msg = { role: 'user', text: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)
    setError(null)
    try {
      const res = await aiClient.chat(sessionId, input)
      const replyText = res.reply || res.message || res.text || 'No response'
      const assistantMsg: Msg = { role: 'assistant', text: replyText }
      setMessages((prev) => {
        const merged = [...prev, assistantMsg]
        // keep last 10 turns per requirement
        return merged.slice(-20)
      })
    } catch (e: any) {
      setError(e?.message || 'Assistant error')
      setMessages((prev) => [...prev, { role: 'assistant', text: `Error: ${e?.message || 'unknown error'}` }])
    } finally {
      setLoading(false)
    }
  }

  const tools = useMemo(() => ['estimate workload', 'recommend offers', 'parse workload'], [])

  return (
    <div className="border rounded p-4 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold">AI Assistant</h3>
          <p className="text-xs text-gray-500">Session: {sessionId.slice(0, 8)}…</p>
        </div>
        <div className="flex gap-1 text-xs text-gray-600">
          {tools.map((t) => (
            <span key={t} className="px-2 py-1 rounded bg-gray-100">{t}</span>
          ))}
        </div>
      </div>

      <div ref={scrollRef} className="h-64 overflow-auto mb-3 space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <div
              className={`inline-block px-3 py-2 rounded-2xl max-w-[80%] ${
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {!messages.length && (
          <div className="text-sm text-gray-500">Ask for GPU recommendations, workload sizing, or price comparisons.</div>
        )}
      </div>

      {error && <div className="text-xs text-red-600 mb-2">{error}</div>}

      <div className="flex gap-2">
        <input
          className="input-field flex-1"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
        />
        <button className="btn-primary" onClick={send} disabled={loading}>
          {loading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
