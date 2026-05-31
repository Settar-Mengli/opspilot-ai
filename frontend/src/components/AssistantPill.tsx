import { BulBulAvatar } from './BulBulAvatar'

interface Props {
  assistantName: string
}

export function AssistantPill({ assistantName }: Props) {
  return (
    <div className="assistant-pill">
      <BulBulAvatar size={24} />
      <span className="av-name">{assistantName}</span>
      <span className="av-status">
        · <span className="av-live-dot"></span>on duty
      </span>
    </div>
  )
}
