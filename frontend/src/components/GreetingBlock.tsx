import { BulBulAvatar } from './BulBulAvatar'

interface GreetingBlockProps {
  userName: string
  assistantName: string
  salutation: string
  warmth?: string
  urgencyLine?: string
  timeWindowLine?: string
  dayShapeLine?: string
  credibilityLine?: string
  /** When false, omit the Sample badge (Google connected). Default true. */
  showSampleBadge?: boolean
}

export function GreetingBlock({
  userName,
  assistantName,
  salutation,
  warmth,
  urgencyLine,
  timeWindowLine,
  dayShapeLine,
  credibilityLine,
  showSampleBadge = true,
}: GreetingBlockProps) {
  return (
    <section className="greeting-block">
      <div className="greeting-header">
        <BulBulAvatar size={56} assistantName={assistantName} />
        <h1 className="greeting-headline">
          {salutation}{userName ? `, ${userName}` : ''}.
        </h1>
      </div>
      {(warmth || urgencyLine || timeWindowLine) && (
        <p className="greeting-body">
          {warmth ? <span>{warmth} </span> : null}
          {urgencyLine ? <span>{urgencyLine} </span> : null}
          {timeWindowLine ? <span>{timeWindowLine}</span> : null}
        </p>
      )}
      {dayShapeLine ? (
        <p className="greeting-dayshape">
          {showSampleBadge ? (
            <span className="sample-badge" aria-label="Sample data">Sample</span>
          ) : null}
          {dayShapeLine}
        </p>
      ) : null}
      {credibilityLine ? <p className="greeting-credibility">{credibilityLine}</p> : null}
    </section>
  )
}
