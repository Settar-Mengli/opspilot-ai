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
  if (!raw) return 'Unknown time'
  try {
    const d = new Date(raw)
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return raw
  }
}

export function RunHistoryPanel({ runs, selectedRunId, isLoading, error, onSelectRun }: RunHistoryPanelProps) {
  return (
    <section className="panel">
      <div className="run-history-header">
        <h3>Run History</h3>
        <button type="button" className="drawer-close" onClick={() => onSelectRun(null)} disabled={!selectedRunId}>
          Use Latest
        </button>
      </div>

      {isLoading ? <p className="muted">Loading run history...</p> : null}
      {error ? <p className="muted">{error}</p> : null}

      {!isLoading && !error && runs.length === 0 ? <p className="muted">No historical runs available yet.</p> : null}

      {!isLoading && !error && runs.length > 0 ? (
        <ul className="run-history-list">
          {runs.slice(0, 12).map((run) => {
            const isActive = run.run_id === selectedRunId
            const itemCount = typeof run.item_count === 'number' ? run.item_count : null
            const isFailed = run.status === 'failed'
            return (
              <li key={run.run_id}>
                <button
                  type="button"
                  className={`run-history-item${isActive ? ' run-history-item-active' : ''}`}
                  onClick={() => onSelectRun(run.run_id)}
                >
                  <span className={`run-history-dot${isFailed ? ' failed' : ''}`} />
                  <span className="run-history-info">
                    <span className="run-history-id">{run.run_id}</span>
                    <span className="run-history-meta">{formatRunTimestamp(run)}</span>
                  </span>
                  {itemCount !== null && (
                    <span className="run-history-badge">{itemCount} items</span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
