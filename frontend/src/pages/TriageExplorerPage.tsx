import { useEffect, useMemo, useState } from 'react'
import { getRunTriage, getTriage } from '../api/client'
import type { Category, TriageRecord, Urgency } from '../api/types'
import { ExplainabilityDrawer } from '../components/ExplainabilityDrawer'

interface TriageExplorerPageProps {
  refreshToken: number
  selectedRunId: string | null
  onSelectLatest: () => void
}

const URGENCY_FILTERS: Array<Urgency | 'all'> = ['all', 'critical', 'high', 'medium', 'low']
const CATEGORY_FILTERS: Array<Category | 'all'> = ['all', 'incident', 'request', 'admin', 'follow_up', 'other']

const CATEGORY_LABELS: Record<Category | 'all', string> = {
  all: 'all',
  incident: 'incident',
  request: 'request',
  admin: 'admin',
  follow_up: 'follow up',
  other: 'other',
}

export function TriageExplorerPage({ refreshToken, selectedRunId, onSelectLatest }: TriageExplorerPageProps) {
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [selectedUrgency, setSelectedUrgency] = useState<Urgency | 'all'>('all')
  const [selectedCategory, setSelectedCategory] = useState<Category | 'all'>('all')
  const [selectedRecord, setSelectedRecord] = useState<TriageRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const triage = selectedRunId ? await getRunTriage(selectedRunId) : await getTriage()
        if (!cancelled) {
          setRecords(triage)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load triage records')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadData()

    return () => {
      cancelled = true
    }
  }, [refreshToken, selectedRunId])

  const filtered = useMemo(() => {
    return records.filter((record) => {
      const urgencyMatch = selectedUrgency === 'all' || record.urgency === selectedUrgency
      const categoryMatch = selectedCategory === 'all' || record.category === selectedCategory
      return urgencyMatch && categoryMatch
    })
  }, [records, selectedUrgency, selectedCategory])

  const urgencyCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 }
    for (const r of records) {
      counts[r.urgency] = (counts[r.urgency] || 0) + 1
    }
    return counts
  }, [records])

  if (loading) {
    return <div className="page-state">Loading triage records...</div>
  }

  if (error) {
    return (
      <div className="page-state page-error">
        <p>{error}</p>
        {selectedRunId ? (
          <button type="button" className="drawer-close" onClick={onSelectLatest}>
            Return to Latest
          </button>
        ) : null}
      </div>
    )
  }

  return (
    <div className="triage-layout">
      <div className="page-header">
        <h1 className="page-title">Triage Explorer</h1>
        <p className="page-subtitle">
          {selectedRunId ? `Historical snapshot: ${selectedRunId}` : 'Inspect how each work item was classified and why.'}
        </p>
      </div>

      <div className="triage-summary">
        <span className="triage-summary-total">{records.length} items</span>
        {urgencyCounts.critical > 0 && <span className="urgency-chip critical">{urgencyCounts.critical} critical</span>}
        {urgencyCounts.high > 0 && <span className="urgency-chip high">{urgencyCounts.high} high</span>}
        {urgencyCounts.medium > 0 && <span className="urgency-chip medium">{urgencyCounts.medium} medium</span>}
        {urgencyCounts.low > 0 && <span className="urgency-chip low">{urgencyCounts.low} low</span>}
      </div>

      <div className="filter-bar">
        <select
          className="filter-select"
          value={selectedUrgency}
          onChange={(event) => setSelectedUrgency(event.target.value as Urgency | 'all')}
        >
          {URGENCY_FILTERS.map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
        <select
          className="filter-select"
          value={selectedCategory}
          onChange={(event) => setSelectedCategory(event.target.value as Category | 'all')}
        >
          {CATEGORY_FILTERS.map((value) => (
            <option key={value} value={value}>{CATEGORY_LABELS[value]}</option>
          ))}
        </select>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Urgency</th>
            <th>Category</th>
            <th>Sentiment</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((record) => (
            <tr
              key={record.id}
              tabIndex={0}
              role="button"
              aria-label={`View explainability details for ${record.id}`}
              onClick={() => setSelectedRecord(record)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  setSelectedRecord(record)
                }
              }}
            >
              <td>{record.id}</td>
              <td>
                <span className={`urgency-chip ${record.urgency}`}>{record.urgency}</span>
              </td>
              <td>{record.category}</td>
              <td>{record.sentiment}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <ExplainabilityDrawer record={selectedRecord} onClose={() => setSelectedRecord(null)} />
    </div>
  )
}
