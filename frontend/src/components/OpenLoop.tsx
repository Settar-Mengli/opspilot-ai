import type { TriageRecord } from '../api/types'

interface Props {
  number: number
  record: TriageRecord
}

export function OpenLoop({ number, record }: Props) {
  // Map urgency to a "due" label
  const dueLabel = record.urgency === 'critical' ? 'First thing'
    : record.urgency === 'high' ? 'By end of day'
    : 'When you can'

  return (
    <div className="loop">
      <div className="loop-top">
        <div className="loop-num">{number}</div>
        <div className="loop-body">
          <div className="loop-title">{record.id}</div>
          <div className="loop-desc">{record.urgency_reason}</div>
          <div className="loop-meta">
            <span className="chip">{record.category}</span>
            <span className="chip due">{dueLabel}</span>
          </div>
        </div>
        <div className="loop-action">
          <svg className="arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
      </div>
    </div>
  )
}
