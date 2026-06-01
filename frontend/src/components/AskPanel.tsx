import { useCallback, useEffect, useRef, useState } from 'react'
import { askOpsPilot } from '../api/client'
import type { AskMessage } from '../api/types'

interface Props {
  open: boolean
  assistantName: string
  initialQuestion: string
  onClose: () => void
}

export function AskPanel({ open, assistantName, initialQuestion, onClose }: Props) {
  const [messages, setMessages] = useState<AskMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const hasSentInitial = useRef(false)

  const sendQuestion = useCallback(async (question: string) => {
    const clean = question.trim()
    if (!clean) return
    setError(null)
    const userMsg: AskMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: clean,
      timestamp: Date.now(),
    }
    setMessages(m => [...m, userMsg])
    setInput('')
    setLoading(true)
    try {
      const answer = await askOpsPilot(clean, assistantName)
      const assistantMsg: AskMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: answer || 'I did not get a response. Please try again.',
        timestamp: Date.now(),
      }
      setMessages(m => [...m, assistantMsg])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }, [assistantName])

  // Auto-send initialQuestion on mount (component remounts each session via key)
  useEffect(() => {
    if (initialQuestion.trim() && !hasSentInitial.current) {
      hasSentInitial.current = true
      sendQuestion(initialQuestion.trim())
    }
  }, [initialQuestion, sendQuestion])

  // Focus input after mount
  useEffect(() => {
    const t = setTimeout(() => inputRef.current?.focus(), 200)
    return () => clearTimeout(t)
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Scroll-lock + Escape-to-close
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  function handleSubmit() {
    if (loading) return
    sendQuestion(input)
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className={`ask-panel-overlay ${open ? 'open' : ''}`} onClick={onClose}>
      <div className="ask-panel" onClick={(e) => e.stopPropagation()}>
        <div className="ask-panel-header">
          <div className="ask-panel-title">
            <span className="ask-panel-orb">{assistantName.charAt(0).toUpperCase()}</span>
            <span>Ask {assistantName}</span>
          </div>
          <button className="ask-panel-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="ask-panel-messages">
          {messages.length === 0 && !loading && (
            <div className="ask-panel-empty">
              I have visibility into your current triage queue. Ask me about priorities, patterns, or what to focus on.
            </div>
          )}
          {messages.map(msg => (
            <div key={msg.id} className={`ask-msg ask-msg-${msg.role}`}>
              <div className="ask-msg-bubble">{msg.text}</div>
            </div>
          ))}
          {loading && (
            <div className="ask-msg ask-msg-assistant">
              <div className="ask-msg-bubble ask-msg-thinking">
                <span className="ask-dot"></span>
                <span className="ask-dot"></span>
                <span className="ask-dot"></span>
              </div>
            </div>
          )}
          {error && (
            <div className="ask-panel-error">
              {error}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="ask-panel-input-row">
          <input
            ref={inputRef}
            className="ask-panel-input"
            placeholder={`Ask ${assistantName} anything…`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
          />
          <button
            className="ask-panel-send"
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            aria-label="Send"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5"></line>
              <polyline points="5 12 12 5 19 12"></polyline>
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
