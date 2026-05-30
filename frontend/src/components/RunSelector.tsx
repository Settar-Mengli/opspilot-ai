import type { RunSummary } from '../api/types'

interface RunSelectorProps {
  runs: RunSummary[]
  selectedRunId: string | null
  isLoading: boolean
  error: string | null
  onSelectRun: (runId: string | null) => void
}

function toRunLabel(run: RunSummary): string {
  const timestamp = run.finished_at ?? run.started_at ?? 'unknown time'
  const status = run.status ?? 'unknown'
  const itemCount = typeof run.item_count === 'number' ? `items ${run.item_count}` : 'items n/a'
  return `${run.run_id} | ${status} | ${timestamp} | ${itemCount}`
}

export function RunSelector({ runs, selectedRunId, isLoading, error, onSelectRun }: RunSelectorProps) {
  const hasSelectedRun = Boolean(selectedRunId)
  const hasOptionForSelected = hasSelectedRun && runs.some((run) => run.run_id === selectedRunId)

  return (
    <label className="run-selector-label">
      <span>Run</span>
      <select
        className="run-selector"
        value={selectedRunId ?? ''}
        onChange={(event) => onSelectRun(event.target.value || null)}
        disabled={isLoading}
        aria-label="Select run snapshot"
      >
        <option value="">Latest</option>
        {hasSelectedRun && !hasOptionForSelected ? <option value={selectedRunId ?? ''}>{selectedRunId}</option> : null}
        {runs.map((run) => (
          <option key={run.run_id} value={run.run_id}>
            {toRunLabel(run)}
          </option>
        ))}
      </select>
      {error ? <span className="run-selector-error">{error}</span> : null}
    </label>
  )
}
