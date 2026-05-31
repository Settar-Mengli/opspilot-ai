interface Props {
  userName?: string | null
  assistantName: string
  dateLabel: string
  briefing: string
}

export function Greeting({ userName, assistantName, dateLabel, briefing }: Props) {
  // Render briefing with **bold** turned into <strong>
  const renderBriefing = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>
      }
      return <span key={i}>{part}</span>
    })
  }

  const greetingText = userName ? `Good morning, ${userName}.` : 'Good morning.'

  return (
    <div className="greeting fade-in d2">
      <div className="greeting-row">
        <div className="g-name">{greetingText}</div>
        <div className="g-date">{dateLabel}</div>
      </div>
      <div className="g-text">{renderBriefing(briefing)}</div>
      <div className="g-byline">
        <div className="g-byline-dot">{assistantName.charAt(0).toUpperCase()}</div>
        <span>{assistantName} · 2 minutes ago</span>
      </div>
    </div>
  )
}
