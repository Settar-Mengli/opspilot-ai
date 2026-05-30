import { useEffect, useMemo, useState } from 'react'
import { getBriefing, getRunBriefing, getRunTriage, getTriage } from '../api/client'
import type { RunSummary, TriageRecord } from '../api/types'
import { RunHistoryPanel } from '../components/RunHistoryPanel'
import { UrgencyDistribution } from '../components/UrgencyDistribution'
import { parseBriefing } from '../utils/briefing'

interface DashboardPageProps {
  refreshToken: number
  selectedRunId: string | null
  runs: RunSummary[]
  runsLoading: boolean
  runsError: string | null
  onSelectRun: (runId: string | null) => void
}

export function DashboardPage({ refreshToken, selectedRunId, runs, runsLoading, runsError, onSelectRun }: DashboardPageProps) {
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
        const [triageData, briefingText] = selectedRunId
          ? await Promise.all([getRunTriage(selectedRunId), getRunBriefing(selectedRunId)])
          : await Promise.all([getTriage(), getBriefing()])
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
  }, [refreshToken, selectedRunId])

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
    return (
      <div className="page-state page-error">
        <p>{error}</p>
        {selectedRunId ? (
          <button type="button" className="drawer-close" onClick={() => onSelectRun(null)}>
            Return to Latest
          </button>
        ) : null}
      </div>
    )
  }

  return (
    <div className="page-grid">
      <section className="panel hero-panel">
        <h2>OpsPilot Mission</h2>
        <p className="hero-copy">
          OpsPilot turns operational work items into explainable priorities, action queues, and executive-ready daily briefings.
        </p>
        <div className="how-it-works" aria-label="How OpsPilot works">
          <span>Input Work Items</span>
          <span>Triage &amp; Explainability</span>
          <span>Executive Briefing</span>
        </div>
      </section>

      <section className="kpi-grid">
        <article className="kpi-card">
          <span>Total Work Items</span>
          <strong>{metrics.total}</strong>
        </article>
        <article className="kpi-card">
          <span>Critical Risks</span>
          <strong>{metrics.critical}</strong>
        </article>
        <article className="kpi-card">
          <span>High Priority Items</span>
          <strong>{metrics.high}</strong>
        </article>
        <article className="kpi-card">
          <span>Negative Sentiment Signals</span>
          <strong>{metrics.negative}</strong>
        </article>
      </section>

      <section className="panel">
        <h3>Top Operational Risks</h3>
        <p className="muted section-intro">
          {selectedRunId
            ? `Top operational risks detected from historical run ${selectedRunId}.`
            : 'Top operational risks detected from the latest run.'}
        </p>
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

      <RunHistoryPanel
        runs={runs}
        selectedRunId={selectedRunId}
        isLoading={runsLoading}
        error={runsError}
        onSelectRun={onSelectRun}
      />

      <UrgencyDistribution triage={triage} />
    </div>
  )
}
