import { useEffect } from 'react'
import type { TriageRecord } from '../api/types'
import { BulBulAvatar } from './BulBulAvatar'
import { ArrowRight } from 'lucide-react'

function numberWord(n: number): string {
  const words = ['zero','one','two','three','four','five','six','seven','eight','nine','ten']
  return n >= 2 && n <= 10 ? words[n] : String(n)
}

const ordinals = ['First','Second','Third','Fourth','Fifth','Sixth','Seventh','Eighth','Ninth','Tenth']

interface Props {
  open: boolean
  records: TriageRecord[]
  onClose: () => void
}

export function PrioritiesPanel({ open, records, onClose }: Props) {
  // Scroll-lock + Escape-to-close
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onClose])

  if (!open) return null

  const urgent = records.filter(r => r.urgency === 'critical' || r.urgency === 'high')

  const introText = urgent.length === 0
    ? "Nothing urgent right now — your queue is calm."
    : urgent.length === 1
      ? "Here's the one I'd want you to see."
      : `Here are the ${numberWord(urgent.length)} I'd want you to see. I'd start with the first.`

  return (
    <div className="slide-panel-backdrop" onClick={onClose}>
      <div className="slide-panel" onClick={e => e.stopPropagation()}>
        <div className="slide-panel-header">
          <h2 className="slide-panel-title">The {urgent.length === 1 ? 'one thing' : `${numberWord(urgent.length)} things`}</h2>
          <button className="slide-panel-close" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="slide-panel-body">
          <div className="priorities-intro">
            <BulBulAvatar size={26} />
            <p className="priorities-intro-txt">{introText}</p>
          </div>

          {urgent.map((r, i) => (
            <div key={r.id} className={`pcard${i === 0 ? ' pcard--lead' : ''}`}>
              <div className="pcard-top">
                <span className="pnum">{ordinals[i] ?? `#${i + 1}`}</span>
                <span className={`ppill ${r.urgency === 'critical' ? 'ppill--crit' : 'ppill--high'}`}>
                  {r.urgency === 'critical' ? 'Critical' : 'High'}
                </span>
              </div>
              <p className="ptitle2">{r.id}</p>
              <p className="pwhy">{r.urgency_reason}</p>
              <div className="paction">
                <span className="paction-ic"><ArrowRight size={16} strokeWidth={2} /></span>
                <p className="paction-txt">Ask me and I'll help you work through this.</p>
              </div>
            </div>
          ))}

          <div className="pfoot">
            <BulBulAvatar size={26} />
            <p className="pfoot-txt">That's everything urgent. The rest can wait — I'm holding it.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
