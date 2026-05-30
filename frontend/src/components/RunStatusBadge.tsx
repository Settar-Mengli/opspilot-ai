interface RunStatusBadgeProps {
  selectedRunId: string | null
}

export function RunStatusBadge({ selectedRunId }: RunStatusBadgeProps) {
  if (!selectedRunId) {
    return <span className="run-status-badge run-status-latest">Latest</span>
  }

  return <span className="run-status-badge run-status-historical">Historical</span>
}
