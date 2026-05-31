import { useState } from 'react'

interface Props {
  assistantName: string
  onMicClick: () => void
  onAsk: (question: string) => void
}

export function MobileDock({ assistantName, onMicClick, onAsk }: Props) {
  const [text, setText] = useState('')

  function handleSubmit() {
    const trimmed = text.trim()
    if (!trimmed) return
    onAsk(trimmed)
    setText('')
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="mobile-dock">
      <div className="mobile-ask-pill">
        <div className="ask-icon-sm">{assistantName.charAt(0).toUpperCase()}</div>
        <input
          placeholder={`Ask ${assistantName} anything…`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
        />
      </div>
      {text.trim() ? (
        <button className="mobile-send-btn" onClick={handleSubmit} aria-label="Send">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
          </svg>
        </button>
      ) : (
        <button className="mic-btn" onClick={onMicClick} aria-label="Voice input">
          <svg className="mic-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
        </button>
      )}
    </div>
  )
}
