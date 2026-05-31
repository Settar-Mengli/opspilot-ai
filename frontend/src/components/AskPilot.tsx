import { useState } from 'react'
import type { RefObject } from 'react'

const SUGGESTIONS = [
  'Draft a Slack message about the outage',
  'Reschedule my Thursday 1:1',
  'Summarize today\'s customer threads',
]

interface Props {
  assistantName: string
  inputRef?: RefObject<HTMLInputElement | null>
  onMicClick?: () => void
  onAsk: (question: string) => void
  voiceSupported?: boolean
}

export function AskPilot({ assistantName, inputRef, onMicClick, onAsk, voiceSupported = true }: Props) {
  const [text, setText] = useState('')

  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().includes('MAC')
  const shortcutHint = isMac ? '⌘K' : 'Ctrl+K'

  function handleSubmit() {
    const trimmed = text.trim()
    if (!trimmed) return
    onAsk(trimmed)
    setText('')
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="ask-section fade-in d4">
      <div className="section-label">Ask {assistantName}</div>
      <div className="ask-bar">
        <div className="ask-icon-sm">{assistantName.charAt(0).toUpperCase()}</div>
        <input
          ref={inputRef}
          className="ask-input"
          placeholder={`Ask ${assistantName} anything — draft a message, summarize a thread… ${shortcutHint}`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
        />
        <button className="ask-send" disabled={!text.trim()} onClick={handleSubmit}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
          </svg>
        </button>
        {onMicClick && voiceSupported && (
          <button className="mic-btn-sm" onClick={onMicClick} aria-label="Voice input">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>
        )}
      </div>
      <div className="ask-suggestions">
        {SUGGESTIONS.map(s => (
          <button key={s} className="suggestion-chip" onClick={() => onAsk(s)}>{s}</button>
        ))}
      </div>
    </div>
  )
}
