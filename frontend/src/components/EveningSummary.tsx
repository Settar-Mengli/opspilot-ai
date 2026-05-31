interface Props {
  assistantName: string
  onClick: () => void
}

export function EveningSummary({ assistantName, onClick }: Props) {
  return (
    <button className="evening-card-button fade-in d6" onClick={onClick} type="button">
      <div className="evening-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--blue)' }}>
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </div>
      <div style={{ flex: 1, textAlign: 'left' }}>
        <div className="evening-label">{assistantName} · End of day summary</div>
        <div className="evening-text">Tap to wrap up your day.</div>
      </div>
    </button>
  )
}
