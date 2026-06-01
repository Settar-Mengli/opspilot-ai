import { useEffect, useState } from 'react'
import { getAiBriefing, getTriage } from '../api/client'
import { BulBulAvatar } from '../components/BulBulAvatar'
import { BriefingSkeleton } from '../components/skeletons/BriefingSkeleton'

function formatDate(): string {
  const d = new Date()
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${days[d.getDay()]}, ${months[d.getMonth()]} ${d.getDate()}`
}

function renderPara(para: string, i: number) {
  const parts = para.split(/(\*\*[^*]+\*\*)/g)
  return (
    <p key={i} className="br-para">
      {parts.map((p, j) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return <strong key={j} className="br-para-bold">{p.slice(2, -2)}</strong>
        }
        return <span key={j}>{p}</span>
      })}
    </p>
  )
}

export function BriefingPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<{ critical: number; high: number; canWait: number } | null>(null)

  useEffect(() => {
    let cancelled = false

    const briefingP = getAiBriefing()
    const triageP = getTriage()

    briefingP
      .then(t => { if (!cancelled) setText(t) })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load briefing') })

    triageP
      .then(records => {
        if (cancelled) return
        let critical = 0, high = 0, canWait = 0
        for (const r of records) {
          if (r.urgency === 'critical') critical++
          else if (r.urgency === 'high') high++
          else canWait++
        }
        setMetrics({ critical, high, canWait })
      })
      .catch(() => { /* metrics unavailable — render without them */ })

    Promise.allSettled([briefingP, triageP]).then(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [])

  if (loading) return <BriefingSkeleton />

  if (error) {
    return <div className="page-state page-error"><p>{error}</p></div>
  }

  const paragraphs = text ? text.split(/\n\n+/).map(p => p.trim()).filter(Boolean) : []
  const summary = paragraphs.length > 0 ? paragraphs[0] : "Here's your read for today."
  const body = paragraphs.slice(1)

  return (
    <div className="br-page">
      <div className="br-header">
        <p className="br-title">Today's briefing</p>
        <span className="br-date">{formatDate()}</span>
      </div>

      <div className="br-summary">
        <BulBulAvatar size={32} />
        <p className="br-summary-txt">{summary}</p>
      </div>

      {metrics && (
        <div className="br-metrics">
          <div className="br-metric">
            <p className="br-metric-num br-n-crit">{metrics.critical}</p>
            <p className="br-metric-lab">Critical</p>
          </div>
          <div className="br-metric">
            <p className="br-metric-num br-n-high">{metrics.high}</p>
            <p className="br-metric-lab">High</p>
          </div>
          <div className="br-metric">
            <p className="br-metric-num br-n-rest">{metrics.canWait}</p>
            <p className="br-metric-lab">Can wait</p>
          </div>
        </div>
      )}

      {body.length > 0 && (
        <div className="br-sec-wrap">
          <p className="br-sec">Today's read</p>
          <div className="br-body">
            {body.map((para, i) => renderPara(para, i))}
          </div>
        </div>
      )}

      <div className="br-foot">
        <BulBulAvatar size={26} />
        <p className="br-foot-txt">That's the whole read. Ask me about any of it.</p>
      </div>
    </div>
  )
}
