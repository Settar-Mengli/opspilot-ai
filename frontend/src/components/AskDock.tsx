import { useEffect, useRef } from 'react'
import type { AskDraftCard, AskMessage, AskToolStep } from '../api/types'
import { ASK_APPROVE_ENABLED } from '../api/askStream'

export interface AskThreadProps {
  assistantName: string
  messages: AskMessage[]
  toolSteps?: AskToolStep[]
  draft?: AskDraftCard | null
  onDraftSubjectChange?: (value: string) => void
  onDraftBodyChange?: (value: string) => void
  onApproveDraft?: () => void
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
  toolSteps = [],
  draft = null,
  onDraftSubjectChange,
  onDraftBodyChange,
  onApproveDraft,
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
  }, [messages, loading, toolSteps, draft])

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
        {messages.length === 0 && !loading && toolSteps.length === 0 && !draft && (
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
        {toolSteps.length > 0 && (
          <ol className="ask-tool-timeline" aria-label="Tool steps">
            {toolSteps.map((step) => (
              <li key={step.id} className={`ask-tool-step ask-tool-step-${step.status}`}>
                <span className="ask-tool-name">{step.tool}</span>
                <span className="ask-tool-status">{step.status}</span>
              </li>
            ))}
          </ol>
        )}
        {draft && (
          <div className="ask-draft-card" data-testid="ask-draft-card">
            <div className="ask-draft-title">Draft reply</div>
            <label className="ask-draft-label">
              Subject
              <input
                className="ask-draft-input"
                value={draft.subject}
                onChange={(e) => onDraftSubjectChange?.(e.target.value)}
                aria-label="Draft subject"
                disabled={Boolean(draft.sentAt)}
              />
            </label>
            <label className="ask-draft-label">
              Body
              <textarea
                className="ask-draft-textarea"
                value={draft.body}
                onChange={(e) => onDraftBodyChange?.(e.target.value)}
                rows={4}
                aria-label="Draft body"
                disabled={Boolean(draft.sentAt)}
              />
            </label>
            <p className="ask-draft-meta" aria-live="polite">
              To: {draft.toAddrs} (server-managed)
              {draft.sentAt ? (
                <>
                  {' '}
                  · Sent ✓{' '}
                  {new Date(draft.sentAt).toLocaleTimeString(undefined, {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </>
              ) : null}
            </p>
            {draft.approveError ? (
              <div className="ask-draft-approve-error" role="alert">
                {draft.approveError}
              </div>
            ) : null}
            <button
              type="button"
              className="ask-draft-approve"
              data-testid="ask-draft-approve"
              disabled={!ASK_APPROVE_ENABLED || Boolean(draft.sentAt) || Boolean(draft.approving)}
              title={
                draft.sentAt
                  ? 'Already sent'
                  : draft.approving
                    ? 'Sending…'
                    : ASK_APPROVE_ENABLED
                      ? 'Approve and send'
                      : 'Approve available after mail HITL lands'
              }
              onClick={() => {
                if (ASK_APPROVE_ENABLED && !draft.sentAt && !draft.approving) onApproveDraft?.()
              }}
            >
              Approve & send
            </button>
          </div>
        )}
        {loading && (
          <div className="ask-msg ask-msg-assistant">
            <div className="ask-msg-bubble ask-msg-thinking">
              <span className="ask-dot" />
              <span className="ask-dot" />
              <span className="ask-dot" />
            </div>
          </div>
        )}
        {error && (
          <div className="ask-panel-error" role="alert">
            {error}
          </div>
        )}
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

type DockProps = AskThreadProps

export function AskDock({ assistantName, ...thread }: DockProps) {
  return (
    <aside className="desk-ask" aria-label="Ask">
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
