import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTriage } from '../api/client'
import type { TriageRecord } from '../api/types'
import { GreetingBlock } from '../components/GreetingBlock'
import { PrioritiesPanel } from '../components/PrioritiesPanel'
import { WeekPanel } from '../components/WeekPanel'
import { getTimeOfDay, getGreetingWord } from '../utils/greeting'
import { Flame, MessageCircle, Eye, Lightbulb, Moon, CalendarDays, FileText } from 'lucide-react'

function numberWord(n: number): string {
  const words = ['zero','one','two','three','four','five','six','seven','eight','nine','ten']
  return n >= 2 && n <= 10 ? words[n] : String(n)
}

interface Props {
  userName?: string | null
  assistantName: string
  onAsk: (question: string) => void
  onEveningClick: () => void
}

export function DashboardPage({ userName, assistantName, onAsk, onEveningClick }: Props) {
  const navigate = useNavigate()
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [prioritiesOpen, setPrioritiesOpen] = useState(false)
  const [weekOpen, setWeekOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    getTriage()
      .then(t => { if (!cancelled) setRecords(t) })
      .catch(e => { if (!cancelled) console.error(e) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const urgentCount = records.filter(r => r.urgency === 'critical' || r.urgency === 'high').length
  const heldCount = records.filter(r => r.urgency === 'medium' || r.urgency === 'low').length

  const salutation = getGreetingWord(getTimeOfDay())
  const displayName = userName ?? ''

  const warmth = "It's good to see you."

  const urgencyLine = loading
    ? undefined
    : urgentCount === 0
      ? "Your queue is clear right now."
      : urgentCount === 1
        ? "There's one thing I'd like you to see when you're ready."
        : `There are ${numberWord(urgentCount)} things I'd like you to see when you're ready.`

  const dayShapeLine = "Today is light. Friday is where the week tightens — Q3 close lands."

  const credibilityLine = loading
    ? undefined
    : heldCount === 0
      ? undefined
      : heldCount === 1
        ? "I held one small thing off your queue this morning. I'll surface them only if they need you."
        : `I held ${numberWord(heldCount)} small things off your queue this morning. I'll surface them only if they need you.`

  // Tile 1 label
  const tile1Label = loading
    ? 'Priorities'
    : urgentCount === 0
      ? 'Nothing to flag yet'
      : urgentCount === 1
        ? 'The one thing'
        : `The ${numberWord(urgentCount)} things`

  const tile1Subtitle = urgentCount === 0
    ? 'Your queue is clear'
    : "I'll walk you through them"

  return (
    <div className="dashboard-redesign">
      <GreetingBlock
        userName={displayName}
        assistantName={assistantName}
        salutation={salutation}
        warmth={warmth}
        urgencyLine={urgencyLine}
        dayShapeLine={dayShapeLine}
        credibilityLine={credibilityLine}
      />

      <p className="dash-section-header">Where would you like to start?</p>

      {/* Choice tiles — 2×2 grid */}
      <section className="dash-tiles">
        <button
          className={`dash-tile${urgentCount > 0 ? ' dash-tile--urgent' : ''}`}
          onClick={() => setPrioritiesOpen(true)}
        >
          {urgentCount > 0 && <span className="dash-tile-icon dash-tile-icon--olive"><Flame size={20} strokeWidth={2} /></span>}
          <span className={`dash-tile-label${urgentCount > 0 ? ' dash-tile-label--olive' : ''}`}>{tile1Label}</span>
          <span className="dash-tile-subtitle">{tile1Subtitle}</span>
        </button>

        <button className="dash-tile" onClick={() => onAsk('')}>
          <span className="dash-tile-icon"><MessageCircle size={20} strokeWidth={2} /></span>
          <span className="dash-tile-label">Just ask me</span>
          <span className="dash-tile-subtitle">Anything on your mind</span>
        </button>

        <button className="dash-tile" onClick={() => navigate('/items')}>
          <span className="dash-tile-icon"><Eye size={20} strokeWidth={2} /></span>
          <span className="dash-tile-label">The full picture</span>
          <span className="dash-tile-subtitle">{loading ? 'All items, nothing hidden' : `All ${records.length} items, nothing hidden`}</span>
        </button>

        <button className="dash-tile" onClick={() => navigate('/insights')}>
          <span className="dash-tile-icon"><Lightbulb size={20} strokeWidth={2} /></span>
          <span className="dash-tile-label">What I'm noticing</span>
          <span className="dash-tile-subtitle">A few patterns worth your time</span>
        </button>
      </section>

      {/* Ghost links */}
      <section className="dash-ghost-links">
        <button className="dash-ghost-link" onClick={onEveningClick}><Moon size={14} strokeWidth={2} /> Wrap up the day</button>
        <span className="dash-ghost-sep"> · </span>
        <button className="dash-ghost-link" onClick={() => setWeekOpen(true)}><CalendarDays size={14} strokeWidth={2} /> The whole week</button>
        <span className="dash-ghost-sep"> · </span>
        <button className="dash-ghost-link" onClick={() => navigate('/briefing')}><FileText size={14} strokeWidth={2} /> Today's briefing</button>
      </section>

      {/* Slide-up panels */}
      <PrioritiesPanel open={prioritiesOpen} records={records} onClose={() => setPrioritiesOpen(false)} />
      <WeekPanel open={weekOpen} onClose={() => setWeekOpen(false)} />
    </div>
  )
}
