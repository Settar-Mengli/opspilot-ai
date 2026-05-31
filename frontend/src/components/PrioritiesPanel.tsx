import type { TriageRecord } from '../api/types'

interface Props {
  open: boolean
  records: TriageRecord[]
  onClose: () => void
}

export function PrioritiesPanel({ open, records, onClose }: Props) {
  if (!open) return null

  const urgent = records.filter(r => r.urgency === 'critical' || r.urgency === 'high')

  return (
    <div className="slide-panel-backdrop" onClick={onClose}>
      <div className="slide-panel" onClick={e => e.stopPropagation()}>
        <div className="slide-panel-header">
          <h2 className="slide-panel-title">Priorities</h2>
          <button className="slide-panel-close" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="slide-panel-body">
          {urgent.length === 0 ? (
            <p className="slide-panel-empty">Nothing urgent right now. Enjoy the calm.</p>
          ) : (
            <ul className="priorities-list">
              {urgent.map(r => (
                <li key={r.id} className="priorities-item">
                  <span className="priorities-id">{r.id}</span>
                  <span className="priorities-reason">{r.urgency_reason}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
