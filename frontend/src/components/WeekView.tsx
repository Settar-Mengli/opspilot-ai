import type { TriageRecord } from '../api/types'

interface Props {
  records: TriageRecord[]
}

export function WeekView({ records }: Props) {
  const urgent = records.filter(r => r.urgency === 'critical' || r.urgency === 'high')
  const inFlight = records.filter(r => r.urgency === 'medium')
  const resolved = records.filter(r => r.urgency === 'low')

  return (
    <div className="week-summary fade-in d3">
      <div className="week-summary-card">
        <div className="week-summary-label">Needs attention</div>
        <div className="week-summary-count">{urgent.length}</div>
        <div className="week-summary-desc">
          {urgent.length === 0
            ? 'Nothing flagged urgent this week.'
            : urgent.length === 1
              ? 'One item flagged for executive attention.'
              : `${urgent.length} items flagged for executive attention.`}
        </div>
      </div>

      <div className="week-summary-card">
        <div className="week-summary-label">In flight</div>
        <div className="week-summary-count">{inFlight.length}</div>
        <div className="week-summary-desc">
          {inFlight.length === 0
            ? 'No active mid-priority items.'
            : `${inFlight.length} ${inFlight.length === 1 ? 'item is' : 'items are'} moving through the system.`}
        </div>
      </div>

      <div className="week-summary-card">
        <div className="week-summary-label">Resolved</div>
        <div className="week-summary-count">{resolved.length}</div>
        <div className="week-summary-desc">
          {resolved.length === 0
            ? 'No items closed yet this period.'
            : `${resolved.length} ${resolved.length === 1 ? 'item has' : 'items have'} been resolved or de-prioritized.`}
        </div>
      </div>

      <div className="week-summary-note">
        Calendar integration arrives in a future release — meetings, prep blocks, and forward-looking conflicts will live here.
      </div>
    </div>
  )
}
