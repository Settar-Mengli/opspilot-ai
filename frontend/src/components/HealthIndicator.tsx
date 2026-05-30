interface HealthIndicatorProps {
  isHealthy: boolean
  isLoading: boolean
}

export function HealthIndicator({ isHealthy, isLoading }: HealthIndicatorProps) {
  const label = isLoading ? 'Checking API' : isHealthy ? 'API Healthy' : 'API Unavailable'
  const statusClassName = isLoading ? 'status-dot status-dot-loading' : isHealthy ? 'status-dot status-dot-ok' : 'status-dot status-dot-error'

  return (
    <div className="health-indicator" role="status" aria-live="polite">
      <span className={statusClassName} />
      <span>{label}</span>
    </div>
  )
}
