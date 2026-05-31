interface Notification {
  id: string
  text: string
  time: string
}

interface Props {
  open: boolean
  notifications: Notification[]
}

export function NotifyPanel({ open, notifications }: Props) {
  return (
    <div className={`notify-panel ${open ? 'open' : ''}`}>
      <div className="notify-head">
        Pilot's observations <span>{notifications.length} new</span>
      </div>
      {notifications.map(n => (
        <div className="notify-item" key={n.id}>
          <div className="notify-dot"></div>
          <div>
            <div className="notify-text">{n.text}</div>
            <div className="notify-time">{n.time}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
