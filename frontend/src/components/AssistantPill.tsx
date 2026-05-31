interface Props {
  assistantName: string
}

export function AssistantPill({ assistantName }: Props) {
  const initial = assistantName.charAt(0).toUpperCase()
  return (
    <div className="assistant-pill">
      <div className="av-mark">{initial}</div>
      <span className="av-name">{assistantName}</span>
      <span className="av-status">
        · <span className="av-live-dot"></span>on duty
      </span>
    </div>
  )
}
