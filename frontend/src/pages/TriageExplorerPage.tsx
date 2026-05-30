import { useEffect, useMemo, useState } from 'react'
import { getTriage } from '../api/client'
import type { Category, TriageRecord, Urgency } from '../api/types'
import { ExplainabilityDrawer } from '../components/ExplainabilityDrawer'

interface TriageExplorerPageProps {
  refreshToken: number
}

const URGENCY_FILTERS: Array<Urgency | 'all'> = ['all', 'critical', 'high', 'medium', 'low']
const CATEGORY_FILTERS: Array<Category | 'all'> = ['all', 'incident', 'request', 'admin', 'follow-up', 'other']

export function TriageExplorerPage({ refreshToken }: TriageExplorerPageProps) {
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
        const triage = await getTriage()
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
  }, [refreshToken])

  const filtered = useMemo(() => {
    return records.filter((record) => {
      const urgencyMatch = selectedUrgency === 'all' || record.urgency === selectedUrgency
      const categoryMatch = selectedCategory === 'all' || record.category === selectedCategory
      return urgencyMatch && categoryMatch
    })
  }, [records, selectedUrgency, selectedCategory])

  if (loading) {
    return <div className="page-state">Loading triage records...</div>
  }

  if (error) {
    return <div className="page-state page-error">{error}</div>
  }

  return (
    <div className="triage-layout">
      <section className="panel">
        <div className="filter-row">
          <label>
            Urgency
            <select value={selectedUrgency} onChange={(event) => setSelectedUrgency(event.target.value as Urgency | 'all')}>
              {URGENCY_FILTERS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category
            <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value as Category | 'all')}>
              {CATEGORY_FILTERS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="table-wrap">
          <table>
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
                <tr key={record.id} onClick={() => setSelectedRecord(record)}>
                  <td>{record.id}</td>
                  <td>
                    <span className={`urgency-chip urgency-${record.urgency}`}>{record.urgency}</span>
                  </td>
                  <td>{record.category}</td>
                  <td>{record.sentiment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <ExplainabilityDrawer record={selectedRecord} onClose={() => setSelectedRecord(null)} />
    </div>
  )
}
