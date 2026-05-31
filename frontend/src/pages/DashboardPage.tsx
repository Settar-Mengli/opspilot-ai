import { useEffect, useMemo, useState } from 'react'
import { getBriefing, getInputFiles, getRunBriefing, getRunTriage, getTriage, runPipeline } from '../api/client'
import type { RunSummary, TriageRecord } from '../api/types'
import { RunHistoryPanel } from '../components/RunHistoryPanel'
import { UrgencyDistribution } from '../components/UrgencyDistribution'
import { parseBriefing } from '../utils/briefing'

interface DashboardPageProps {
  refreshToken: number
  selectedRunId: string | null
  runs: RunSummary[]
  runsLoading: boolean
  runsError: string | null
  onSelectRun: (runId: string | null) => void
  onRefresh: () => void
}

export function DashboardPage({ refreshToken, selectedRunId, runs, runsLoading, runsError, onSelectRun, onRefresh }: DashboardPageProps) {
  const [triage, setTriage] = useState<TriageRecord[]>([])
  const [briefing, setBriefing] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Run Pipeline state
  const [inputFiles, setInputFiles] = useState<string[]>([])
  const [selectedInput, setSelectedInput] = useState('')
  const [runDate, setRunDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [runLoading, setRunLoading] = useState(false)
  const [runSuccess, setRunSuccess] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function loadInputs() {
      try {
        const files = await getInputFiles()
        if (!cancelled) {
          setInputFiles(files)
          if (files.length > 0 && !selectedInput) {
            setSelectedInput(files[0])
          }
        }
      } catch {
        // Non-critical - run panel just won't show files
      }
    }
    void loadInputs()
    return () => { cancelled = true }
  }, [])

  async function handleRunPipeline() {
    if (!selectedInput) return
    setRunLoading(true)
    setRunSuccess(false)
    setRunError(null)
    try {
      await runPipeline(selectedInput, runDate)
      setRunSuccess(true)
      onRefresh()
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Pipeline run failed')
    } finally {
      setRunLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)
      try {
        const [triageData, briefingText] = selectedRunId
          ? await Promise.all([getRunTriage(selectedRunId), getRunBriefing(selectedRunId)])
          : await Promise.all([getTriage(), getBriefing()])
        if (!cancelled) {
          setTriage(triageData)
          setBriefing(briefingText)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard data')
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

  const metrics = useMemo(() => {
    return {
      total: triage.length,
      critical: triage.filter((entry) => entry.urgency === 'critical').length,
      high: triage.filter((entry) => entry.urgency === 'high').length,
      negative: triage.filter((entry) => entry.sentiment === 'negative').length,
    }
  }, [triage])

  const parsedBriefing = useMemo(() => parseBriefing(briefing), [briefing])

  if (loading) {
    return <div className="page-state">Loading dashboard data...</div>
  }

  if (error) {
    return (
      <div className="page-state page-error">
        <p>{error}</p>
        {selectedRunId ? (
          <button type="button" className="drawer-close" onClick={() => onSelectRun(null)}>
            Return to Latest
          </button>
        ) : null}
      </div>
    )
  }

  return (
    <div>
      <section className="run-panel">
        <span className="run-panel-label">Run Pipeline</span>
        <select
          className="run-select"
          value={selectedInput}
          onChange={(e) => setSelectedInput(e.target.value)}
          disabled={runLoading}
        >
          {inputFiles.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
        <input
          type="date"
          className="run-date-input"
          value={runDate}
          onChange={(e) => setRunDate(e.target.value)}
          disabled={runLoading}
        />
        <button
          type="button"
          className="btn-run"
          onClick={handleRunPipeline}
          disabled={runLoading || !selectedInput}
        >
          {runLoading ? 'Running...' : '\u25B6 Run Pipeline'}
        </button>
        {runSuccess && <span className="run-status-success">{'\u2713'} Pipeline complete</span>}
        {runError && <span className="run-status-error">{runError}</span>}
      </section>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">TOTAL WORK ITEMS</div>
          <div className="kpi-value">{metrics.total}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">CRITICAL RISKS</div>
          <div className="kpi-value critical">{metrics.critical}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">HIGH PRIORITY</div>
          <div className="kpi-value high">{metrics.high}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">NEGATIVE SENTIMENT</div>
          <div className="kpi-value negative">{metrics.negative}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Top Operational Risks</div>
        <div className="card-subtitle">
          {selectedRunId
            ? `Risks detected from historical run ${selectedRunId}.`
            : 'Risks detected from the latest run.'}
        </div>
        {parsedBriefing.topPriorities.length === 0 ? (
          <p style={{ fontSize: '13px', color: 'var(--t3)' }}>No priority items available.</p>
        ) : (
          <div className="risk-list">
            {parsedBriefing.topPriorities.map((item, i) => (
              <div key={i} className="risk-item">
                <span className={`risk-dot ${i < metrics.critical ? 'critical' : 'high'}`} />
                <span>{item}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <RunHistoryPanel
        runs={runs}
        selectedRunId={selectedRunId}
        isLoading={runsLoading}
        error={runsError}
        onSelectRun={onSelectRun}
      />

      <UrgencyDistribution triage={triage} />
    </div>
  )
}
