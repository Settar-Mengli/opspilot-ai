import { useEffect, useId, useRef, useState } from 'react'
import { useOverlay } from '../hooks/useOverlay'
import { BulBulAvatar } from './BulBulAvatar'
import { getCalendarWeek } from '../api/client'
import type { CalendarMeeting } from '../api/types'

interface DayView {
  abbrev: string
  num: number
  mood: string
  note: string
  segments: ('low' | 'mid' | 'high' | 'off')[]
  emphasis?: string
  variant?: 'today' | 'tight'
  showLine: boolean
}

function buildDays(meetings: CalendarMeeting[]): { days: DayView[]; sample: boolean } {
  const now = new Date()
  const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  const days: DayView[] = []
  const abbrevs = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  for (let i = 0; i < 5; i += 1) {
    const dayStart = new Date(start.getTime() + i * 86400000)
    const dayEnd = new Date(dayStart.getTime() + 86400000)
    const dayMeetings = meetings.filter((m) => {
      const s = new Date(m.start_at).getTime()
      return s >= dayStart.getTime() && s < dayEnd.getTime()
    })
    const count = dayMeetings.length
    const segments: DayView['segments'] =
      count === 0 ? ['off', 'off', 'off'] : count === 1 ? ['low', 'off', 'off'] : count === 2 ? ['mid', 'mid', 'off'] : ['high', 'high', 'high']
    const titles = dayMeetings.map((m) => m.title).slice(0, 2)
    days.push({
      abbrev: abbrevs[dayStart.getUTCDay()] ?? 'Day',
      num: dayStart.getUTCDate(),
      mood: count === 0 ? 'Light' : count >= 3 ? 'Heavy' : 'Building',
      note: titles.length ? titles.join(' · ') : 'Quiet day.',
      segments,
      variant: i === 0 ? 'today' : count >= 3 ? 'tight' : undefined,
      emphasis: count >= 3 ? 'Busy.' : undefined,
      showLine: i < 4,
    })
  }
  return { days, sample: meetings.length === 0 }
}

interface Props {
  open: boolean
  onClose: () => void
}

export function WeekPanel({ open, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const { onBackdropClick } = useOverlay({ open, onClose, containerRef: panelRef })
  const [days, setDays] = useState<DayView[]>([])
  const [sample, setSample] = useState(true)

  useEffect(() => {
    if (!open) return
    const now = new Date()
    const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
    const end = new Date(start.getTime() + 7 * 86400000)
    let cancelled = false
    getCalendarWeek(start.toISOString(), end.toISOString())
      .then((meetings) => {
        if (cancelled) return
        const built = buildDays(meetings)
        setDays(built.days)
        setSample(built.sample)
      })
      .catch(() => {
        if (cancelled) return
        const built = buildDays([])
        setDays(built.days)
        setSample(true)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  if (!open) return null

  return (
    <div className="slide-panel-backdrop" onClick={onBackdropClick}>
      <div
        ref={panelRef}
        className="slide-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={e => e.stopPropagation()}
      >
        <div className="slide-panel-header">
          <h2 className="slide-panel-title" id={titleId}>The whole week</h2>
          <button className="slide-panel-close" onClick={onClose} aria-label="Close panel">✕</button>
        </div>
        <div className="slide-panel-body">
          <div className="wk-intro">
            <BulBulAvatar size={32} />
            <p className="wk-intro-txt">
              {sample && <span className="sample-badge" aria-label="Sample data">Sample</span>}
              {sample
                ? 'No calendar events synced yet. Connect Google and sync to fill this week.'
                : 'Your next five days from Google Calendar.'}
            </p>
          </div>

          {days.map(day => (
            <div className="wk-day" key={`${day.abbrev}-${day.num}`}>
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
        </div>
      </div>
    </div>
  )
}
