import type { TriageRecord, Urgency } from '../api/types'

interface UrgencyDistributionProps {
  triage: TriageRecord[]
}

const URGENCY_ORDER: Urgency[] = ['critical', 'high', 'medium', 'low']

export function UrgencyDistribution({ triage }: UrgencyDistributionProps) {
  const total = triage.length || 1

  const counts = URGENCY_ORDER.map((urgency) => {
    const count = triage.filter((record) => record.urgency === urgency).length
    const percentage = Math.round((count / total) * 100)
    return { urgency, count, percentage }
  })

  return (
    <div className="panel">
      <h3>Urgency Distribution</h3>
      <div className="distribution-list">
        {counts.map((item) => (
          <div key={item.urgency} className="distribution-row">
            <div className="distribution-label">
              <span className={`urgency-chip ${item.urgency}`}>{item.urgency}</span>
              <span>{item.count} ({item.percentage}%)</span>
            </div>
            <div className="distribution-track">
              <div className={`distribution-fill ${item.urgency}`} style={{ width: `${item.percentage}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
