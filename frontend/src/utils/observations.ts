import type { TriageRecord } from '../api/types'

export interface Observation {
  id: string
  text: string
  time: string
}

export function deriveObservations(records: TriageRecord[]): Observation[] {
  if (records.length === 0) return []

  const observations: Observation[] = []

  const criticalCount = records.filter(r => r.urgency === 'critical').length
  const highCount = records.filter(r => r.urgency === 'high').length

  // Observation 1 — counts
  if (criticalCount > 0) {
    observations.push({
      id: 'urgent-count',
      text: `${criticalCount} ${criticalCount === 1 ? 'item is' : 'items are'} flagged critical and ${criticalCount === 1 ? 'needs' : 'need'} attention.`,
      time: 'just now',
    })
  } else if (highCount > 0) {
    observations.push({
      id: 'urgent-count',
      text: `${highCount} high-priority ${highCount === 1 ? 'item is' : 'items are'} open.`,
      time: 'just now',
    })
  } else {
    observations.push({
      id: 'urgent-count',
      text: `No urgent items right now. Everything is moving steadily.`,
      time: 'just now',
    })
  }

  // Observation 2 — categories
  const categories = new Set(records.map(r => r.category).filter(Boolean))
  if (categories.size > 0) {
    const categoryList = Array.from(categories).slice(0, 3).join(', ')
    observations.push({
      id: 'categories',
      text: `Activity across ${categories.size} ${categories.size === 1 ? 'area' : 'areas'}: ${categoryList}.`,
      time: '5 minutes ago',
    })
  }

  // Observation 3 — accountability gap (items with no clear owner indication)
  const negativeSignals = records.filter(r =>
    (r.urgency === 'critical' || r.urgency === 'high') && r.urgency_reason
  ).length
  if (negativeSignals >= 2) {
    observations.push({
      id: 'pattern',
      text: `${negativeSignals} items signal urgency — worth reviewing whether ownership is clear across them.`,
      time: '15 minutes ago',
    })
  }

  return observations.slice(0, 3)
}
