import { useState } from 'react'

export function MemoryChip() {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="memory-chip-wrap fade-in d5">
      <button className="memory-chip" onClick={() => setExpanded(o => !o)} aria-expanded={expanded}>
        <div className="memory-icon">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-3)' }}>
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2z"/>
            <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2z"/>
          </svg>
        </div>
        <div className="memory-text">
          <strong>Pilot remembers</strong> your preferences and adapts over time.
        </div>
        <span className="memory-count">12 prefs</span>
        <svg className={`memory-chevron ${expanded ? 'open' : ''}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>
      <div className={`memory-panel ${expanded ? 'open' : ''}`}>
        <p>
          I'm just getting started. I'll learn your preferences as we work together —
          how you like messages drafted, what times you take meetings, which decisions
          you delegate. Come back in a few days and you'll see what I've learned.
        </p>
      </div>
    </div>
  )
}
