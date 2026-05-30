interface HealthIndicatorProps {
  isHealthy: boolean
  isLoading: boolean
}

export function HealthIndicator({ isHealthy, isLoading }: HealthIndicatorProps) {
  const label = isLoading ? 'Checking API' : isHealthy ? 'API Healthy' : 'API Unavailable'
  const dotClass = isLoading ? 'health-dot' : isHealthy ? 'health-dot healthy' : 'health-dot unhealthy'

  return (
    <div className="health-indicator" role="status" aria-live="polite">
      <span className={dotClass} />
      <span>{label}</span>
    </div>
  )
}
