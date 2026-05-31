interface Props {
  open: boolean
  onClose: () => void
}

export function VoiceOverlay({ open, onClose }: Props) {
  return (
    <div className={`voice-overlay ${open ? 'open' : ''}`}>
      <div className="voice-orb">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-1)' }}>
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        </svg>
      </div>
      <div className="voice-status">Listening</div>
      <div className="voice-text">Voice input coming soon — this is a preview of the experience.</div>
      <button className="voice-close" onClick={onClose}>Tap to close</button>
    </div>
  )
}
