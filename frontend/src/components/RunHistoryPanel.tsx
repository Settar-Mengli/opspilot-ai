import type { RunSummary } from '../api/types'

interface RunHistoryPanelProps {
  runs: RunSummary[]
  selectedRunId: string | null
  isLoading: boolean
  error: string | null
  onSelectRun: (runId: string | null) => void
}

function formatRunTimestamp(run: RunSummary): string {
  return run.finished_at ?? run.started_at ?? 'Unknown time'
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
            const itemCount = typeof run.item_count === 'number' ? run.item_count : 'n/a'
            return (
              <li key={run.run_id}>
                <button
                  type="button"
                  className={`run-history-item${isActive ? ' run-history-item-active' : ''}`}
                  onClick={() => onSelectRun(run.run_id)}
                >
                  <strong>{run.run_id}</strong>
                  <span>{run.status ?? 'unknown'} | {formatRunTimestamp(run)} | items {itemCount}</span>
                </button>
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
