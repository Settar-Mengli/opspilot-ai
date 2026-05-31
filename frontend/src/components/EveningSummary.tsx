interface Props {
  assistantName: string
}

export function EveningSummary({ assistantName }: Props) {
  return (
    <div className="evening-card fade-in d6">
      <div className="evening-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--blue)' }}>
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </div>
      <div style={{ flex: 1 }}>
        <div className="evening-label">{assistantName} · End of day summary</div>
        <div className="evening-text">I'll prepare your closing summary at 6 PM.</div>
      </div>
      <div className="evening-time">in 4h 22m</div>
    </div>
  )
}
