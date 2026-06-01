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
      {dayShapeLine ? <p className="greeting-dayshape">{dayShapeLine}</p> : null}
      {credibilityLine ? <p className="greeting-credibility">{credibilityLine}</p> : null}
    </section>
  )
}
