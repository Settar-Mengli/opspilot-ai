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
  focusToken?: number
  variant?: 'modal' | 'dock'
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
  variant = 'modal',
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
      <div className={variant === 'dock' ? 'desk-ask-body' : 'ask-panel-messages'}>
        {messages.length === 0 && !loading && (
          <div className={variant === 'dock' ? 'desk-ask-empty' : 'ask-panel-empty'}>
            {variant === 'dock' ? (
              <>
                <div className="desk-ask-orb" aria-hidden>
                  {assistantName.charAt(0).toUpperCase()}
                </div>
                <p>
                  I have visibility into your current triage queue. Ask me about priorities,
                  patterns, or what to focus on.
                </p>
              </>
            ) : (
              'I have visibility into your current triage queue. Ask me about priorities, patterns, or what to focus on.'
            )}
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
      <div className={variant === 'dock' ? 'desk-ask-footer' : 'ask-panel-input-row'}>
        <input
          ref={ref}
          className={variant === 'dock' ? 'desk-ask-input' : 'ask-panel-input'}
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
      <AskThreadBody assistantName={assistantName} variant="dock" {...thread} />
    </aside>
  )
}
