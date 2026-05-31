interface Props {
  open: boolean
  onClose: () => void
}

export function WeekPanel({ open, onClose }: Props) {
  if (!open) return null

  return (
    <div className="slide-panel-backdrop" onClick={onClose}>
      <div className="slide-panel" onClick={e => e.stopPropagation()}>
        <div className="slide-panel-header">
          <h2 className="slide-panel-title">This Week</h2>
          <button className="slide-panel-close" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="slide-panel-body">
          <p className="slide-panel-empty">
            Week view with calendar integration arrives in a future release.
          </p>
        </div>
      </div>
    </div>
  )
}
