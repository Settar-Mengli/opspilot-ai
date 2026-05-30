import { useEffect, useMemo, useState } from 'react'
import { getBriefing, getTriage } from '../api/client'
import type { TriageRecord } from '../api/types'
import { UrgencyDistribution } from '../components/UrgencyDistribution'
import { parseBriefing } from '../utils/briefing'

interface DashboardPageProps {
  refreshToken: number
}

export function DashboardPage({ refreshToken }: DashboardPageProps) {
  const [triage, setTriage] = useState<TriageRecord[]>([])
  const [briefing, setBriefing] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const [triageData, briefingText] = await Promise.all([getTriage(), getBriefing()])
        if (!cancelled) {
          setTriage(triageData)
          setBriefing(briefingText)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard data')
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

  const metrics = useMemo(() => {
    return {
      total: triage.length,
      critical: triage.filter((entry) => entry.urgency === 'critical').length,
      high: triage.filter((entry) => entry.urgency === 'high').length,
      negative: triage.filter((entry) => entry.sentiment === 'negative').length,
    }
  }, [triage])

  const parsedBriefing = useMemo(() => parseBriefing(briefing), [briefing])

  if (loading) {
    return <div className="page-state">Loading dashboard data...</div>
  }

  if (error) {
    return <div className="page-state page-error">{error}</div>
  }

  return (
    <div className="page-grid">
      <section className="kpi-grid">
        <article className="kpi-card">
          <span>Total Items</span>
          <strong>{metrics.total}</strong>
        </article>
        <article className="kpi-card">
          <span>Critical</span>
          <strong>{metrics.critical}</strong>
        </article>
        <article className="kpi-card">
          <span>High</span>
          <strong>{metrics.high}</strong>
        </article>
        <article className="kpi-card">
          <span>Negative Sentiment</span>
          <strong>{metrics.negative}</strong>
        </article>
      </section>

      <section className="panel">
        <h3>Top Priorities</h3>
        {parsedBriefing.topPriorities.length === 0 ? (
          <p className="muted">No priority items available.</p>
        ) : (
          <ul className="priority-list">
            {parsedBriefing.topPriorities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </section>

      <UrgencyDistribution triage={triage} />
    </div>
  )
}
