import { useId, useRef } from 'react'
import { useOverlay } from '../hooks/useOverlay'

interface Notification {
  id: string
  text: string
  time: string
}

interface Props {
  open: boolean
  notifications: Notification[]
  assistantName: string
  onClose: () => void
}

export function NotifyPanel({ open, notifications, assistantName, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  useOverlay({ open, onClose, lockScroll: false, containerRef: panelRef })

  return (
    <div
      ref={panelRef}
      className={`notify-panel ${open ? 'open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      hidden={!open}
    >
      <div className="notify-head" id={titleId}>
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
