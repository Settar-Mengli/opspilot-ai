import type { RunSummary } from '../api/types'

interface RunHistoryPanelProps {
  runs: RunSummary[]
  selectedRunId: string | null
  isLoading: boolean
  error: string | null
  onSelectRun: (runId: string | null) => void
}

function formatRunTimestamp(run: RunSummary): string {
  const raw = run.finished_at ?? run.started_at
  if (!raw) return 'Unknown'
  try {
    const d = new Date(raw)
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return raw
  }
}

export function RunHistoryPanel({ runs, selectedRunId, isLoading, error, onSelectRun }: RunHistoryPanelProps) {
  return (
    <div className="card">
      <div className="card-title">Run History</div>

      {isLoading && <p style={{ fontSize: '12px', color: 'var(--t3)' }}>Loading...</p>}
      {error && <p style={{ fontSize: '12px', color: 'var(--critical)' }}>{error}</p>}

      {!isLoading && !error && runs.length === 0 && (
        <p style={{ fontSize: '12px', color: 'var(--t3)' }}>No historical runs available yet.</p>
      )}

      {!isLoading && !error && runs.length > 0 && (
        <div className="run-history-list">
          {runs.slice(0, 12).map((run) => {
            const isActive = run.run_id === selectedRunId
            const itemCount = typeof run.item_count === 'number' ? run.item_count : null
            return (
              <div
                key={run.run_id}
                className={`run-history-item${isActive ? ' selected' : ''}`}
                onClick={() => onSelectRun(run.run_id)}
              >
                <span className="run-dot" />
                <span className="run-id">{run.run_id}</span>
                <span className="run-time">{formatRunTimestamp(run)}</span>
                {itemCount !== null && <span className="run-badge">{itemCount} items</span>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
