interface Notification {
  id: string
  text: string
  time: string
}

interface Props {
  open: boolean
  notifications: Notification[]
  assistantName: string
}

export function NotifyPanel({ open, notifications, assistantName }: Props) {
  return (
    <div className={`notify-panel ${open ? 'open' : ''}`}>
      <div className="notify-head">
        {assistantName}'s observations <span>{notifications.length} new</span>
      </div>
      {notifications.length === 0 ? (
        <div className="notify-empty">
          Nothing notable right now. I'll let you know when something changes.
        </div>
      ) : (
        notifications.map(n => (
          <div className="notify-item" key={n.id}>
            <div className="notify-dot"></div>
            <div>
              <div className="notify-text">{n.text}</div>
              <div className="notify-time">{n.time}</div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
