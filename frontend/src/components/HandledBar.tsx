interface Props {
  count: number
}

export function HandledBar({ count }: Props) {
  return (
    <div className="handled-bar fade-in d4">
      <div className="handled-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      </div>
      <div className="handled-text">
        <strong>{count} other items are in flight.</strong> Nothing else needs you right now.
      </div>
    </div>
  )
}
