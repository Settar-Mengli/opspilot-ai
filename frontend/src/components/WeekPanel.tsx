import { useEffect } from 'react'
import { BulBulAvatar } from './BulBulAvatar'

interface DayData {
  abbrev: string
  num: number
  segments: ('low' | 'mid' | 'high' | 'off')[]
  mood: string
  note: string
  emphasis?: string
  variant?: 'today' | 'tight'
  showLine: boolean
}

const WEEK: DayData[] = [
  { abbrev: 'Mon', num: 2, segments: ['low', 'off', 'off'], mood: 'Today · light', note: 'Two things need you. Room to think.', variant: 'today', showLine: true },
  { abbrev: 'Tue', num: 3, segments: ['low', 'off', 'off'], mood: 'Light', note: 'Quiet. A good day to get ahead of Friday.', showLine: true },
  { abbrev: 'Wed', num: 4, segments: ['mid', 'mid', 'off'], mood: 'Building', note: 'The Northwind sync and two reviews land.', showLine: true },
  { abbrev: 'Thu', num: 5, segments: ['high', 'high', 'high'], mood: 'Heavy', emphasis: 'The tight one.', note: 'Q3 prep, the contract decision, back-to-back.', variant: 'tight', showLine: true },
  { abbrev: 'Fri', num: 6, segments: ['high', 'high', 'off'], mood: 'Q3 close', note: 'Q3 close lands. Everything earlier feeds this.', variant: 'tight', showLine: false },
]

interface Props {
  open: boolean
  onClose: () => void
}

export function WeekPanel({ open, onClose }: Props) {
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

  return (
    <div className="slide-panel-backdrop" onClick={onClose}>
      <div className="slide-panel" onClick={e => e.stopPropagation()}>
        <div className="slide-panel-header">
          <h2 className="slide-panel-title">The whole week</h2>
          <button className="slide-panel-close" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="slide-panel-body">
          <div className="wk-intro">
            <BulBulAvatar size={32} />
            <p className="wk-intro-txt">It starts gentle and tightens toward Friday. If you protect any day, protect Thursday.</p>
          </div>

          {WEEK.map(day => (
            <div className="wk-day" key={day.abbrev}>
              <div className="wk-left">
                <p className="wk-date">{day.abbrev}</p>
                <p className="wk-dnum">{day.num}</p>
                {day.showLine && <div className="wk-line" />}
              </div>
              <div className={`wk-card${day.variant === 'today' ? ' wk-card--today' : day.variant === 'tight' ? ' wk-card--tight' : ''}`}>
                <div className="wk-card-top">
                  <div className="wk-bar">
                    {day.segments.map((seg, i) => (
                      <span key={i} className={`wk-seg${seg !== 'off' ? ` on-${seg}` : ''}`} />
                    ))}
                  </div>
                  <span className="wk-mood">{day.mood}</span>
                </div>
                <p className="wk-note">
                  {day.emphasis && <span className="wk-note-em">{day.emphasis} </span>}
                  {day.note}
                </p>
              </div>
            </div>
          ))}

          <div className="wk-foot">
            <BulBulAvatar size={26} />
            <p className="wk-foot-txt">I'll keep Friday in view all week so it doesn't sneak up.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
