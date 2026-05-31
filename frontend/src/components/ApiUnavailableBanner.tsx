interface Props {
  visible: boolean
  onRetry: () => void
}

export function ApiUnavailableBanner({ visible, onRetry }: Props) {
  if (!visible) return null
  return (
    <div className="api-banner">
      <span>API unavailable. OpsPilot could not reach the local backend.</span>
      <button className="btn-retry" onClick={onRetry}>Retry</button>
    </div>
  )
}
