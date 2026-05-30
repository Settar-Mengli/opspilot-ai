import { useEffect, useState } from 'react'
import { getBriefing, getRunBriefing } from '../api/client'

interface ExecutiveBriefingPageProps {
  refreshToken: number
  selectedRunId: string | null
  onSelectLatest: () => void
}

export function ExecutiveBriefingPage({ refreshToken, selectedRunId, onSelectLatest }: ExecutiveBriefingPageProps) {
  const [briefing, setBriefing] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const text = selectedRunId ? await getRunBriefing(selectedRunId) : await getBriefing()
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
  }, [refreshToken, selectedRunId])

  if (loading) {
    return <div className="page-state">Loading executive briefing...</div>
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
    <section className="briefing-layout">
      <div className="page-header">
        <h1 className="page-title">Executive Briefing</h1>
        <p className="page-subtitle">
          {selectedRunId
            ? `Leadership-ready summary from historical run ${selectedRunId}.`
            : 'Leadership-ready summary generated from the latest operational work items.'}
        </p>
      </div>

      <div className="briefing-content">{briefing}</div>
    </section>
  )
}
