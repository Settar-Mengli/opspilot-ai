interface HealthIndicatorProps {
  isHealthy: boolean
  isLoading: boolean
}

export function HealthIndicator({ isHealthy, isLoading }: HealthIndicatorProps) {
  if (isLoading) {
    return null
  }

  return (
    <div className="health-indicator">
      <span className={`health-dot ${isHealthy ? 'healthy' : 'unhealthy'}`} />
      <span>{isHealthy ? 'API Healthy' : 'API Offline'}</span>
    </div>
  )
}
