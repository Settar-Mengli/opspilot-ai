interface Props {
  open: boolean
  listening: boolean
  transcript: string
  interimTranscript: string
  error: string | null
  onClose: () => void
}

export function VoiceOverlay({ open, listening, transcript, interimTranscript, error, onClose }: Props) {
  const displayText = transcript + interimTranscript
  const showPlaceholder = !displayText.trim() && !error

  return (
    <div className={`voice-overlay ${open ? 'open' : ''}`}>
      <div className={`voice-orb ${listening ? 'listening' : ''}`}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-1)' }}>
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        </svg>
      </div>

      <div className="voice-status">
        {error ? 'Could not hear you' : listening ? 'Listening' : 'Done'}
      </div>

      <div className="voice-text-area">
        {error && <div className="voice-error">{error}</div>}
        {!error && showPlaceholder && (
          <div className="voice-placeholder">Speak now — I'm listening.</div>
        )}
        {!error && !showPlaceholder && (
          <div className="voice-transcript">
            <span className="voice-transcript-final">{transcript}</span>
            <span className="voice-transcript-interim">{interimTranscript}</span>
          </div>
        )}
      </div>

      <button className="voice-close" onClick={onClose}>
        {listening ? 'Tap to stop' : 'Tap to close'}
      </button>
    </div>
  )
}
