export function BriefingSkeleton() {
  return (
    <div className="briefing-skeleton" aria-hidden="true">
      <span className="skeleton skeleton-text skeleton-text-xl skeleton-w-50"></span>
      <div className="briefing-skeleton-paragraph">
        <span className="skeleton skeleton-text skeleton-w-full"></span>
        <span className="skeleton skeleton-text skeleton-w-full"></span>
        <span className="skeleton skeleton-text skeleton-w-90"></span>
      </div>
      <div className="briefing-skeleton-paragraph">
        <span className="skeleton skeleton-text skeleton-w-full"></span>
        <span className="skeleton skeleton-text skeleton-w-80"></span>
        <span className="skeleton skeleton-text skeleton-w-full"></span>
        <span className="skeleton skeleton-text skeleton-w-70"></span>
      </div>
      <div className="briefing-skeleton-paragraph">
        <span className="skeleton skeleton-text skeleton-w-90"></span>
        <span className="skeleton skeleton-text skeleton-w-full"></span>
        <span className="skeleton skeleton-text skeleton-w-60"></span>
      </div>
    </div>
  )
}
