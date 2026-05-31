import { useState } from 'react'

const SUGGESTIONS = [
  'Draft a Slack message about the outage',
  'Reschedule my Thursday 1:1',
  'Summarize today\'s customer threads',
]

export function AskPilot() {
  const [text, setText] = useState('')

  return (
    <div className="ask-section fade-in d4">
      <div className="section-label">Ask Pilot</div>
      <div className="ask-bar">
        <div className="ask-icon-sm">P</div>
        <input
          className="ask-input"
          placeholder="Ask me anything — draft a message, summarize a thread…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="ask-send" disabled={!text.trim()}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
          </svg>
        </button>
      </div>
      <div className="ask-suggestions">
        {SUGGESTIONS.map(s => (
          <button key={s} className="suggestion-chip" onClick={() => setText(s)}>{s}</button>
        ))}
      </div>
    </div>
  )
}
