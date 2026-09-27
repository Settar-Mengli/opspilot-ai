import { useEffect, useId, useRef, useState } from 'react'
import { getEveningSummary } from '../api/client'
import { useOverlay } from '../hooks/useOverlay'
import { BulBulAvatar } from './BulBulAvatar'

interface Props {
  open: boolean
  assistantName: string
  onClose: () => void
}

export function EveningPanel({ open, assistantName, onClose }: Props) {
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()

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

  // Scroll-lock + Escape-to-close via shared overlay hook
  const { onBackdropClick } = useOverlay({ open, onClose, containerRef: panelRef })

  const paragraphs = summary
    ? summary.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
    : []

  return (
    <div
      className={`evening-panel-overlay ${open ? 'open' : ''}`}
      onClick={onBackdropClick}
      aria-hidden={!open}
    >
      <div
        ref={panelRef}
        className="evening-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="evening-panel-header">
          <div className="evening-panel-title" id={titleId}>
            <span>Wrap up the day</span>
          </div>
          <button className="evening-panel-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="evening-panel-body">
          {loading && (
            <div className="ev-intro">
              <BulBulAvatar size={40} />
              <p className="ev-intro-txt">Wrapping up the day…</p>
            </div>
          )}

          {!loading && error && (
            <div className="ev-intro">
              <BulBulAvatar size={40} />
              <p className="ev-intro-txt">{error}</p>
            </div>
          )}

          {!loading && !error && paragraphs.length === 0 && (
            <div className="ev-intro">
              <BulBulAvatar size={40} />
              <p className="ev-intro-txt">Nothing to summarize yet. Once your day has activity, I'll wrap it up here.</p>
            </div>
          )}

          {!loading && !error && paragraphs.length > 0 && (
            <>
              <div className="ev-intro">
                <BulBulAvatar size={40} />
                <p className="ev-intro-txt">{paragraphs[0]}</p>
              </div>

              {paragraphs.length > 1 && (
                <div className="ev-body">
                  {paragraphs.slice(1).map((para, i) => (
                    <p key={i} className="ev-body-para">{para}</p>
                  ))}
                </div>
              )}
            </>
          )}

          <div className="ev-close">
            <BulBulAvatar size={26} />
            <p className="ev-close-txt">Nothing else needs you tonight. Rest — I'll have tomorrow ready when you are.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
