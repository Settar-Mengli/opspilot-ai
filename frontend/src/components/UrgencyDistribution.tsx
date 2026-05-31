import type { TriageRecord, Urgency } from '../api/types'

interface UrgencyDistributionProps {
  triage: TriageRecord[]
}

const URGENCY_ORDER: Urgency[] = ['critical', 'high', 'medium', 'low']

export function UrgencyDistribution({ triage }: UrgencyDistributionProps) {
  const total = triage.length || 1

  const counts = URGENCY_ORDER.map((urgency) => {
    const count = triage.filter((record) => record.urgency === urgency).length
    return { urgency, count }
  })

  return (
    <div className="card">
      <div className="card-title">Urgency Distribution</div>
      {counts.map((item) => (
        <div key={item.urgency} className="urgency-row">
          <span className={`urgency-label-cell ${item.urgency}`}>{item.urgency}</span>
          <div className="urgency-bar-track">
            <div
              className={`urgency-bar-fill ${item.urgency}`}
              style={{ width: `${(item.count / total) * 100}%` }}
            />
          </div>
          <span className="urgency-count">{item.count}</span>
        </div>
      ))}
    </div>
  )
}
