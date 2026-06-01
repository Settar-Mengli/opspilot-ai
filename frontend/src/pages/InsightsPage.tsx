import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getInsights } from '../api/client'
import type { InsightItem } from '../api/types'
import { InsightCardSkeleton } from '../components/skeletons/InsightCardSkeleton'
import { BulBulAvatar } from '../components/BulBulAvatar'
import { TrendingUp, Clock, Eye, Lightbulb, MessageCircle, ArrowLeft } from 'lucide-react'

function categoryChip(category: string): { cls: string; Icon: typeof TrendingUp } {
  const lower = category.toLowerCase()
  if (lower.includes('trend')) return { cls: 'nic--trend', Icon: TrendingUp }
  if (lower.includes('theme') || lower.includes('pattern')) return { cls: 'nic--theme', Icon: Clock }
  if (lower.includes('watch') || lower.includes('risk')) return { cls: 'nic--watch', Icon: Eye }
  return { cls: 'nic--theme', Icon: Lightbulb }
}

interface Props {
  assistantName: string
  onAsk?: (question: string) => void
}

export function InsightsPage({ assistantName, onAsk }: Props) {
  const navigate = useNavigate()
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

  const introText = intro || "A few patterns I've been watching. Nothing urgent — just worth your eye."

  return (
    <>
      <div className="page-header">
        <button className="page-back" onClick={() => navigate('/dashboard')} aria-label="Back to dashboard">
          <ArrowLeft size={20} strokeWidth={2} />
        </button>
        <h2 className="page-header-title">What I'm noticing</h2>
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
          <button className="ni-refresh" onClick={() => { if (!loading) { setLoading(true); loadInsights() } }}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && insights.length === 0 && (
        <div className="ni-intro">
          <BulBulAvatar size={26} />
          <p className="ni-intro-txt">Nothing to surface yet. Once patterns form, I'll bring them here.</p>
        </div>
      )}

      {!loading && !error && insights.length > 0 && (
        <div className="ni-body">
          <div className="ni-intro">
            <BulBulAvatar size={26} />
            <p className="ni-intro-txt">{introText}</p>
          </div>

          {insights.map((insight, i) => {
            const { cls, Icon } = categoryChip(insight.category)
            return (
              <div key={i} className="ni-card">
                <div className="ni-card-top">
                  <span className={`ni-card-ic ${cls}`}><Icon size={17} strokeWidth={2} /></span>
                  <span>
                    <p className="ni-card-tag">{insight.category.toUpperCase()}</p>
                    <p className="ni-card-head">{insight.title}</p>
                  </span>
                </div>
                <p className="ni-note">{insight.body}</p>
                <button
                  className="ni-ask"
                  onClick={() => onAsk?.(`Tell me more about: ${insight.title}`)}
                >
                  <MessageCircle size={14} strokeWidth={2} />
                  Talk it through
                </button>
              </div>
            )
          })}

          <div className="ni-foot">
            <BulBulAvatar size={26} />
            <p className="ni-foot-txt">I'll keep watching. If any of these sharpen, I'll bring it to you.</p>
          </div>
        </div>
      )}
    </>
  )
}
