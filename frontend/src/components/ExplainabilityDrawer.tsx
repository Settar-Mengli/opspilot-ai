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
    <aside className="drawer" aria-label="Explainability details">
      <div className="drawer-header">
        <h3>Explainability</h3>
        <button type="button" className="drawer-close" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="drawer-content">
        <div>
          <p className="muted">Record ID</p>
          <p className="record-id">{record.id}</p>
        </div>
        <div className="reason-block">
          <p className="muted">Urgency</p>
          <p>{record.urgency_reason}</p>
        </div>
        <div className="reason-block">
          <p className="muted">Category</p>
          <p>{record.category_reason}</p>
        </div>
        <div className="reason-block">
          <p className="muted">Sentiment</p>
          <p>{record.sentiment_reason}</p>
        </div>
      </div>
    </aside>
  )
}
