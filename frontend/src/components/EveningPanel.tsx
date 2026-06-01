import { useEffect, useState } from 'react'
import { getEveningSummary } from '../api/client'

interface Props {
  open: boolean
  assistantName: string
  onClose: () => void
}

export function EveningPanel({ open, assistantName, onClose }: Props) {
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Component mounts fresh each time it opens (parent uses conditional render)
  // So we fetch once on mount, no need to track previous open state
  useEffect(() => {
    let cancelled = false
    getEveningSummary(assistantName)
      .then(text => {
        if (!cancelled) setSummary(text)
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Something went wrong.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [assistantName])

  // Scroll-lock + Escape-to-close
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  // Render summary text with paragraph breaks
  const renderSummary = (raw: string) => {
    return raw.split(/\n\n+/).map((para, i) => (
      <p key={i} className="evening-panel-paragraph">
        {para.trim()}
      </p>
    ))
  }

  return (
    <div className={`evening-panel-overlay ${open ? 'open' : ''}`} onClick={onClose}>
      <div className="evening-panel" onClick={(e) => e.stopPropagation()}>
        <div className="evening-panel-header">
          <div className="evening-panel-title">
            <span className="evening-panel-icon" aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
              </svg>
            </span>
            <span>End of day summary</span>
          </div>
          <button className="evening-panel-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="evening-panel-body">
          {loading && (
            <div className="evening-panel-loading">
              <span className="evening-dot"></span>
              <span className="evening-dot"></span>
              <span className="evening-dot"></span>
              <span className="evening-panel-loading-text">
                {assistantName} is wrapping up the day…
              </span>
            </div>
          )}

          {!loading && error && (
            <div className="evening-panel-error">
              {error}
            </div>
          )}

          {!loading && !error && summary && (
            <div className="evening-panel-content">
              {renderSummary(summary)}
            </div>
          )}

          {!loading && !error && !summary && (
            <div className="evening-panel-empty">
              Nothing to summarize yet. Once your day has activity, I'll be able to wrap it up here.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
