interface ApiUnavailableBannerProps {
  visible: boolean
  onRetry: () => void
}

export function ApiUnavailableBanner({ visible, onRetry }: ApiUnavailableBannerProps) {
  if (!visible) {
    return null
  }

  return (
    <div className="api-banner" role="alert">
      <div>
        <strong>API unavailable.</strong> OpsPilot could not reach the local backend.
      </div>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}
