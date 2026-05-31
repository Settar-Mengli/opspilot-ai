import { useEffect, useMemo, useState } from 'react'
import { getTriage, getAiBriefing } from '../api/client'
import type { TriageRecord } from '../api/types'
import { TimeframeTabs } from '../components/TimeframeTabs'
import { Greeting } from '../components/Greeting'
import { OpenLoop } from '../components/OpenLoop'
import { HandledBar } from '../components/HandledBar'
import { QuietState } from '../components/QuietState'
import { AskPilot } from '../components/AskPilot'
import { MemoryChip } from '../components/MemoryChip'
import { EveningSummary } from '../components/EveningSummary'
import { WeekView } from '../components/WeekView'

type View = 'today' | 'tomorrow' | 'week'

const URGENCY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

export function DashboardPage() {
  const [records, setRecords] = useState<TriageRecord[]>([])
  const [briefing, setBriefing] = useState<string>('')
  const [view, setView] = useState<View>('today')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [t, b] = await Promise.all([getTriage(), getAiBriefing()])
        if (!cancelled) {
          setRecords(t)
          setBriefing(b)
        }
      } catch (e) {
        if (!cancelled) {
          console.error(e)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const sorted = useMemo(() => {
    return [...records].sort((a, b) =>
      (URGENCY_ORDER[a.urgency as keyof typeof URGENCY_ORDER] ?? 99) -
      (URGENCY_ORDER[b.urgency as keyof typeof URGENCY_ORDER] ?? 99)
    )
  }, [records])

  const openLoops = sorted.filter(r => r.urgency === 'critical' || r.urgency === 'high').slice(0, 2)
  const inFlightCount = records.length - openLoops.length
  const todayCount = openLoops.length

  // Format today's date
  const today = new Date()
  const dateLabel = today.toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
  })

  // First 250 chars of the AI briefing as the greeting text
  const briefingPreview = briefing.split('\n').filter(l => l.trim()).slice(0, 3).join(' ').slice(0, 280) ||
    `${openLoops.length} ${openLoops.length === 1 ? 'item needs' : 'items need'} you today.`

  return (
    <>
      <TimeframeTabs
        active={view}
        todayCount={todayCount}
        tomorrowCount={1}
        onChange={setView}
      />
      <Greeting dateLabel={dateLabel} briefing={briefingPreview} />

      {view === 'today' && (
        <div className="fade-in d3">
          {openLoops.length > 0 ? (
            <>
              <div className="section-label">
                Open loops <span className="section-count">{openLoops.length} NEED YOU</span>
              </div>
              <div className="loops">
                {openLoops.map((r, i) => <OpenLoop key={r.id} number={i + 1} record={r} />)}
              </div>
              {inFlightCount > 0 && <HandledBar count={inFlightCount} />}
            </>
          ) : (
            <QuietState />
          )}
        </div>
      )}

      {view === 'tomorrow' && (
        <div className="fade-in d3">
          <div className="section-label">
            Tomorrow <span className="section-count">1 ITEM</span>
          </div>
          <QuietState />
        </div>
      )}

      {view === 'week' && (
        <>
          <div className="section-label">Week of June 1 — 5</div>
          <WeekView />
        </>
      )}

      <AskPilot />
      <MemoryChip />
      <EveningSummary />

      {loading && <div style={{ display: 'none' }}>loading...</div>}
    </>
  )
}
