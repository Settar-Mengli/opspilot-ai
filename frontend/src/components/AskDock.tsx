import { useEffect, useRef } from 'react'
import type { AskMessage } from '../api/types'

export interface AskThreadProps {
  assistantName: string
  messages: AskMessage[]
  input: string
  loading: boolean
  error: string | null
  onInputChange: (value: string) => void
  onSubmit: () => void
  inputRef?: React.RefObject<HTMLInputElement | null>
  /** When true, focus the input after mount (docked Ctrl/Cmd+K). */
  focusToken?: number
}

export function AskThreadBody({
  assistantName,
  messages,
  input,
  loading,
  error,
  onInputChange,
  onSubmit,
  inputRef,
  focusToken = 0,
}: AskThreadProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const localInputRef = useRef<HTMLInputElement>(null)
  const ref = inputRef ?? localInputRef

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (focusToken > 0) {
      const t = setTimeout(() => ref.current?.focus(), 50)
      return () => clearTimeout(t)
    }
  }, [focusToken, ref])

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <>
      <div className="ask-panel-messages desk-ask-body">
        {messages.length === 0 && !loading && (
          <div className="desk-ask-empty">
            <div className="desk-ask-orb" aria-hidden>
              {assistantName.charAt(0).toUpperCase()}
            </div>
            <p>
              I have visibility into your current triage queue. Ask me about priorities,
              patterns, or what to focus on.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`ask-msg ask-msg-${msg.role}`}>
            <div className="ask-msg-bubble">{msg.text}</div>
          </div>
        ))}
        {loading && (
          <div className="ask-msg ask-msg-assistant">
            <div className="ask-msg-bubble ask-msg-thinking">
              <span className="ask-dot" />
              <span className="ask-dot" />
              <span className="ask-dot" />
            </div>
          </div>
        )}
        {error && <div className="ask-panel-error">{error}</div>}
        <div ref={messagesEndRef} />
      </div>
      <div className="desk-ask-footer ask-panel-input-row">
        <input
          ref={ref}
          className="ask-panel-input desk-ask-input"
          placeholder={`Ask ${assistantName} anything…`}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          aria-label="Ask input"
        />
        <button
          type="button"
          className="ask-panel-send"
          onClick={onSubmit}
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </>
  )
}

interface DockProps extends AskThreadProps {
  inert?: boolean
}

export function AskDock({ assistantName, inert = false, ...thread }: DockProps) {
  return (
    <aside className="desk-ask" aria-label="Ask" inert={inert || undefined}>
      <div className="desk-ask-header">
        <div className="desk-ask-orb" aria-hidden>
          {assistantName.charAt(0).toUpperCase()}
        </div>
        <div>
          <div className="desk-ask-title">Ask {assistantName}</div>
          <div className="desk-ask-sub">Always available</div>
        </div>
      </div>
      <AskThreadBody assistantName={assistantName} {...thread} />
    </aside>
  )
}
