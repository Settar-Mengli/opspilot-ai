export function LoopSkeleton() {
  return (
    <div className="loop-skeleton" aria-hidden="true">
      <div className="loop-skeleton-num"></div>
      <div className="loop-skeleton-body">
        <span className="skeleton skeleton-text skeleton-text-lg skeleton-w-60"></span>
        <span className="skeleton skeleton-text skeleton-w-90"></span>
        <span className="skeleton skeleton-text skeleton-w-80"></span>
        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
          <span className="skeleton skeleton-text-sm" style={{ width: '70px', borderRadius: '20px', height: '20px' }}></span>
          <span className="skeleton skeleton-text-sm" style={{ width: '90px', borderRadius: '20px', height: '20px' }}></span>
        </div>
      </div>
    </div>
  )
}
