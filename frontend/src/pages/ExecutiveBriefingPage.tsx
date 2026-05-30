import { useEffect, useMemo, useState } from 'react'
import { getBriefing } from '../api/client'
import { parseBriefing } from '../utils/briefing'

interface ExecutiveBriefingPageProps {
  refreshToken: number
}

export function ExecutiveBriefingPage({ refreshToken }: ExecutiveBriefingPageProps) {
  const [briefing, setBriefing] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const text = await getBriefing()
        if (!cancelled) {
          setBriefing(text)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load briefing')
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

  const parsed = useMemo(() => parseBriefing(briefing), [briefing])

  if (loading) {
    return <div className="page-state">Loading executive briefing...</div>
  }

  if (error) {
    return <div className="page-state page-error">{error}</div>
  }

  return (
    <section className="briefing-layout">
      <header className="panel">
        <h2>{parsed.title}</h2>
        <div className="metric-grid">
          <article>
            <span>Total Work Items</span>
            <strong>{parsed.metrics.totalWorkItems}</strong>
          </article>
          <article>
            <span>Urgency Mix</span>
            <strong>{parsed.metrics.urgencyMix}</strong>
          </article>
          <article>
            <span>Sentiment Mix</span>
            <strong>{parsed.metrics.sentimentMix}</strong>
          </article>
        </div>
      </header>

      <section className="panel">
        <h3>Top Priorities</h3>
        <ul className="priority-list">
          {parsed.topPriorities.map((entry) => (
            <li key={entry}>{entry}</li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Due-Soon Action Items</h3>
        {parsed.dueSoon.length === 0 ? (
          <p className="muted">No due-soon action items listed.</p>
        ) : (
          <ul className="priority-list">
            {parsed.dueSoon.map((entry) => (
              <li key={entry}>{entry}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>Raw Briefing</h3>
        <pre className="briefing-raw">{parsed.rawText}</pre>
      </section>
    </section>
  )
}
