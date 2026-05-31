export function QuietState() {
  return (
    <div className="quiet-card fade-in d3">
      <div className="quiet-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>
        </svg>
      </div>
      <div>
        <div className="quiet-title">It's a quiet morning.</div>
        <div className="quiet-text">
          <strong>Nothing needs you right now.</strong> Items in flight are being handled. Enjoy your coffee.
        </div>
      </div>
    </div>
  )
}
