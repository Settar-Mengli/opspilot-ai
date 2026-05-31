import { useEffect, useState, useCallback } from 'react'
import { getInsights } from '../api/client'
import type { InsightItem } from '../api/types'
import { InsightCardSkeleton } from '../components/skeletons/InsightCardSkeleton'

interface Props {
  assistantName: string
}

export function InsightsPage({ assistantName }: Props) {
  const [intro, setIntro] = useState('')
  const [insights, setInsights] = useState<InsightItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)

  const loadInsights = useCallback(() => {
    setRefreshTick(t => t + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    getInsights(assistantName)
      .then(data => {
        if (!cancelled) {
          setIntro(data.intro)
          setInsights(data.insights)
          setError(null)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Something went wrong.')
          setIntro('')
          setInsights([])
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [assistantName, refreshTick])

  function handleRefresh() {
    if (loading) return
    setLoading(true)
    loadInsights()
  }

  return (
    <>
      <div className="insights-header">
        <div>
          <h1 className="insights-title">Insights</h1>
          <p className="insights-subtitle">
            Cross-cutting patterns {assistantName} has noticed in your operational data.
          </p>
        </div>
        <button
          className="insights-refresh"
          onClick={handleRefresh}
          disabled={loading}
          aria-label="Refresh insights"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {loading && (
        <div className="insights-list">
          <InsightCardSkeleton />
          <InsightCardSkeleton />
          <InsightCardSkeleton />
        </div>
      )}

      {!loading && error && (
        <div className="insights-error">
          {error}
        </div>
      )}

      {!loading && !error && intro && (
        <div className="insights-intro fade-in d2">
          {intro}
        </div>
      )}

      {!loading && !error && insights.length === 0 && intro === '' && (
        <div className="insights-empty">
          No insights to show yet. Once your triage data has some history, {assistantName} will surface patterns here.
        </div>
      )}

      {!loading && !error && insights.length > 0 && (
        <div className="insights-list fade-in d3">
          {insights.map((insight, i) => (
            <article key={i} className="insight-card">
              {insight.category && (
                <span className={`insight-category insight-category-${insight.category}`}>
                  {insight.category}
                </span>
              )}
              <h2 className="insight-title">{insight.title}</h2>
              <p className="insight-body">{insight.body}</p>
            </article>
          ))}
        </div>
      )}
    </>
  )
}
