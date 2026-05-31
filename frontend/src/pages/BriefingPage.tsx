import { useEffect, useState } from 'react'
import { getAiBriefing } from '../api/client'
import { BriefingSkeleton } from '../components/skeletons/BriefingSkeleton'

export function BriefingPage() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getAiBriefing()
      .then(t => { if (!cancelled) setText(t) })
      .catch(e => { if (!cancelled) setText(`Error: ${e.message}`) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const renderText = (raw: string) => {
    return raw.split('\n\n').map((para, i) => {
      const parts = para.split(/(\*\*[^*]+\*\*)/g)
      return (
        <p key={i} style={{ marginBottom: '18px', fontFamily: 'var(--font-prose)', fontSize: '15px', lineHeight: 1.8, color: 'var(--text-2)' }}>
          {parts.map((p, j) => {
            if (p.startsWith('**') && p.endsWith('**')) {
              return <strong key={j} style={{ color: 'var(--text-1)', fontWeight: 600 }}>{p.slice(2, -2)}</strong>
            }
            return <span key={j}>{p}</span>
          })}
        </p>
      )
    })
  }

  if (loading) {
    return <BriefingSkeleton />
  }

  return (
    <div className="content-loaded" style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '32px 36px', maxWidth: '800px' }}>
      {renderText(text)}
    </div>
  )
}
