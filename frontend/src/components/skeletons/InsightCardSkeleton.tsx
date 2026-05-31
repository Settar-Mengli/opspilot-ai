export function InsightCardSkeleton() {
  return (
    <div className="insight-card-skeleton" aria-hidden="true">
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <span className="skeleton skeleton-text-sm" style={{ width: '60px', height: '18px', borderRadius: '20px' }}></span>
      </div>
      <span className="skeleton skeleton-text skeleton-text-lg skeleton-w-70" style={{ marginBottom: '12px' }}></span>
      <span className="skeleton skeleton-text skeleton-w-full"></span>
      <span className="skeleton skeleton-text skeleton-w-90"></span>
      <span className="skeleton skeleton-text skeleton-w-60"></span>
    </div>
  )
}
