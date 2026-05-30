import type { TriageRecord } from '../api/types'

interface ExplainabilityDrawerProps {
  record: TriageRecord | null
  onClose: () => void
}

export function ExplainabilityDrawer({ record, onClose }: ExplainabilityDrawerProps) {
  if (!record) {
    return null
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer" aria-label="Explainability details">
        <h3 className="drawer-title">Explainability — {record.id}</h3>
        <div className="drawer-field">
          <p className="drawer-field-label">Urgency</p>
          <p className="drawer-field-value">{record.urgency_reason}</p>
        </div>
        <div className="drawer-field">
          <p className="drawer-field-label">Category</p>
          <p className="drawer-field-value">{record.category_reason}</p>
        </div>
        <div className="drawer-field">
          <p className="drawer-field-label">Sentiment</p>
          <p className="drawer-field-value">{record.sentiment_reason}</p>
        </div>
        <button type="button" className="drawer-close" onClick={onClose}>
          Close
        </button>
      </aside>
    </>
  )
}
